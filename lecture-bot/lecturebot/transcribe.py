"""Speech to text, keeping a timestamp for every segment.

Groq's hosted whisper-large-v3 is used when GROQ_API_KEY is set: an hour of audio takes about a minute
and the full model is more accurate than the turbo model we can afford to run on a CPU. Without a key,
or if Groq fails, faster-whisper runs locally.
"""
import io
import logging
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from . import config

log = logging.getLogger(__name__)
SR = 16000

_model = None
_lock = threading.Lock()

# Hints in the student's field help Whisper keep English terms in Latin letters
# instead of writing them out in Arabic script.
MAJOR_HINTS = {
    "medicine": "محاضرة في الطب، فيها مصطلحات إنجليزية مثل Diagnosis وMitochondria وCardiology وPathology وAnatomy.",
    "engineering": "محاضرة في الهندسة، فيها مصطلحات إنجليزية مثل Stress وVoltage وCircuit وTorque وThermodynamics.",
    "science": "محاضرة في العلوم، فيها مصطلحات إنجليزية مثل DNA وMolecule وEnergy وReaction وEnzyme.",
    "computing": "محاضرة في علوم الحاسب، فيها مصطلحات إنجليزية مثل Algorithm وDatabase وFunction وNetwork وClass.",
    "business": "محاضرة في الإدارة والمحاسبة، فيها مصطلحات إنجليزية مثل Revenue وDepreciation وMarketing وBalance Sheet.",
    "sharia": "درس في العلوم الشرعية، فيه آيات وأحاديث ومصطلحات فقهية وأسماء العلماء.",
    "law": "محاضرة في القانون، فيها مصطلحات قانونية ومواد ونصوص نظامية.",
    "languages": "محاضرة في اللغات والآداب.",
}
DEFAULT_HINT = "محاضرة جامعية باللغة العربية، وقد تحتوي على مصطلحات إنجليزية."

@dataclass
class Segment:
    start: float
    end: float
    text: str


class TranscriptionError(Exception):
    pass


def build_prompt(major: str | None = None, terms: list[str] | None = None) -> str:
    """Context for Whisper. It only reads the last ~224 tokens, so keep it short; terms go last."""
    base = MAJOR_HINTS.get(major or "", DEFAULT_HINT)
    terms = list(terms or [])[:20]
    # ~420 characters stays under Groq's 224-token prompt limit (measured: 377 chars = 172 tokens).
    while terms and len(base) + len("، ".join(terms)) + 20 > 420:
        terms.pop()
    return base + (" مصطلحات المحاضرة: " + "، ".join(terms) + "." if terms else "")


def transcribe(audio: np.ndarray, major: str | None = None, on_progress=None,
               terms: list[str] | None = None) -> list[Segment]:
    """Transcribe 16 kHz mono audio. on_progress(fraction) is called as work completes."""
    prompt = build_prompt(major, terms)
    if config.GROQ_API_KEY:
        try:
            return _transcribe_groq(audio, prompt, on_progress)
        except Exception as e:  # keep the student's job alive: fall back to the local model
            log.warning("Groq transcription failed, using the local model: %s", e)
    return _transcribe_local(audio, prompt, terms, on_progress)


# ---------- Groq ----------

def _split_points(audio: np.ndarray, chunk: int) -> list[int]:
    """Chunk boundaries (in samples), each moved to the quietest moment of the 20 s before it
    so no word is cut in half."""
    n, step, win = len(audio), chunk * SR, 20 * SR
    points, pos = [0], 0
    while n - pos > step + win:
        lo, hi = pos + step - win, pos + step
        frame = SR // 10  # 100 ms
        seg = audio[lo:hi][: (hi - lo) // frame * frame].reshape(-1, frame)
        quiet = int(np.argmin((seg ** 2).mean(axis=1)))
        pos = lo + quiet * frame + frame // 2
        points.append(pos)
    points.append(n)
    return points


def _encode_ogg(audio: np.ndarray) -> bytes:
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
    return subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
         "-c:a", "libopus", "-b:a", "48k", "-f", "ogg", "-"],
        input=pcm, capture_output=True, check=True,
    ).stdout


def _groq_request(data: bytes, prompt: str) -> dict:
    import httpx

    for attempt in range(5):
        r = httpx.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            files={"file": ("audio.ogg", io.BytesIO(data), "audio/ogg")},
            data={"model": config.GROQ_MODEL, "language": "ar", "prompt": prompt, "temperature": "0",
                  "response_format": "verbose_json", "timestamp_granularities[]": "segment"},
            timeout=300,
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 4:
            wait = float(r.headers.get("retry-after") or 2 ** (attempt + 1))
            time.sleep(min(wait, 60))
            continue
        raise TranscriptionError(f"Groq {r.status_code}: {r.text[:300]}")
    raise TranscriptionError("Groq: too many retries")


def _transcribe_groq(audio: np.ndarray, prompt: str, on_progress=None) -> list[Segment]:
    points = _split_points(audio, config.TRANSCRIBE_CHUNK_SECONDS)
    chunks = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    done, lock = [0], threading.Lock()

    def work(bounds):
        lo, hi = bounds
        result = _groq_request(_encode_ogg(audio[lo:hi]), prompt)
        with lock:
            done[0] += 1
            if on_progress:
                on_progress(done[0] / len(chunks))
        offset = lo / SR
        out = []
        for s in result.get("segments", []):
            text = (s.get("text") or "").strip()
            # Whisper invents text over silence; Groq reports how likely a segment is to be silence.
            if text and s.get("no_speech_prob", 0) < 0.8:
                out.append(Segment(offset + s["start"], offset + s["end"], text))
        return out

    with ThreadPoolExecutor(max_workers=config.GROQ_PARALLEL) as pool:
        results = list(pool.map(work, chunks))
    return [s for part in results for s in part]


# ---------- local faster-whisper ----------

def _get_model():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel

            _model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
                cpu_threads=config.WHISPER_THREADS,
            )
        return _model


def _transcribe_local(audio: np.ndarray, prompt: str, terms: list[str] | None, on_progress=None) -> list[Segment]:
    model = _get_model()
    duration = len(audio) / SR or 1.0
    opts = dict(language="ar", initial_prompt=prompt, condition_on_previous_text=False, beam_size=5,
                vad_filter=True, vad_parameters={"threshold": 0.35, "min_silence_duration_ms": 700},
                hotwords=" ".join(terms[:20]) if terms else None)
    if config.WHISPER_BATCH_SIZE > 1:
        from faster_whisper import BatchedInferencePipeline

        segments, _ = BatchedInferencePipeline(model).transcribe(audio, batch_size=config.WHISPER_BATCH_SIZE, **opts)
    else:
        segments, _ = model.transcribe(audio, **opts)
    out: list[Segment] = []
    for s in segments:
        text = s.text.strip()
        if text:
            out.append(Segment(s.start, s.end, text))
        if on_progress:
            on_progress(min(1.0, s.end / duration))
    return out


def to_paragraphs(segments: list[Segment], max_gap: float = 2.5, max_len: int = 600) -> list[Segment]:
    """Merge segments into readable paragraphs, breaking on pauses or length."""
    paras: list[Segment] = []
    for s in segments:
        if paras and s.start - paras[-1].end < max_gap and len(paras[-1].text) < max_len:
            last = paras[-1]
            paras[-1] = Segment(last.start, s.end, f"{last.text} {s.text}")
        else:
            paras.append(Segment(s.start, s.end, s.text))
    return paras
