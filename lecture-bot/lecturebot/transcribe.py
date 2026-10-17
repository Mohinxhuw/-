"""Speech to text with faster-whisper, keeping a timestamp for every segment."""
import threading
from dataclasses import dataclass

import numpy as np

from . import config

_model = None
_lock = threading.Lock()

# Hints in the student's field help Whisper keep English terms in Latin letters
# instead of writing them out in Arabic script.
MAJOR_HINTS = {
    "medicine": "محاضرة في الطب، فيها مصطلحات إنجليزية مثل Diagnosis وMitochondria وCardiology.",
    "engineering": "محاضرة في الهندسة، فيها مصطلحات إنجليزية مثل Stress وVoltage وCircuit.",
    "science": "محاضرة في العلوم، فيها مصطلحات إنجليزية مثل DNA وMolecule وEnergy.",
    "computing": "محاضرة في علوم الحاسب، فيها مصطلحات إنجليزية مثل Algorithm وDatabase وFunction.",
    "business": "محاضرة في الإدارة والمحاسبة، فيها مصطلحات إنجليزية مثل Revenue وDepreciation وMarketing.",
    "sharia": "درس في العلوم الشرعية، فيه آيات وأحاديث ومصطلحات فقهية.",
    "law": "محاضرة في القانون، فيها مصطلحات قانونية.",
    "languages": "محاضرة في اللغات والآداب.",
}
DEFAULT_HINT = "محاضرة جامعية باللغة العربية، وقد تحتوي على مصطلحات إنجليزية."


@dataclass
class Segment:
    start: float
    end: float
    text: str


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


def transcribe(audio: np.ndarray, major: str | None = None, on_progress=None) -> list[Segment]:
    """Transcribe 16 kHz mono audio. on_progress(fraction) is called as segments arrive."""
    model = _get_model()
    duration = len(audio) / 16000 or 1.0
    segments, _info = model.transcribe(
        audio,
        language="ar",
        initial_prompt=MAJOR_HINTS.get(major or "", DEFAULT_HINT),
        vad_filter=True,
        vad_parameters={"threshold": 0.35, "min_silence_duration_ms": 700},
        condition_on_previous_text=False,
        beam_size=5,
    )
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
