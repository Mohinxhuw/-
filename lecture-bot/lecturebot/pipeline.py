"""The full lecture job: audio -> transcript -> study material -> PDF."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import analyze, config, materials as materials_mod, render, transcribe
from .media import SAMPLE_RATE, Source, load_audio, parse_time, probe_duration


class LectureTooLong(Exception):
    pass


@dataclass
class LectureResult:
    analysis: dict
    paragraphs: list
    pdf_path: Path
    transcript_text: str
    source: Source
    extra: dict = field(default_factory=dict)


def safe_name(title: str) -> str:
    name = re.sub(r"[^\w؀-ۿ\- ]+", "", title or "").strip().replace(" ", "_")
    return (name or "lecture")[:60]


def estimate_seconds(duration: float) -> int:
    """ETA shown to the student: transcription plus writing (about 2 minutes, more for long lectures)."""
    per_minute = config.GROQ_SECONDS_PER_AUDIO_MINUTE if config.GROQ_API_KEY else config.WHISPER_SECONDS_PER_AUDIO_MINUTE
    return int(duration / 60 * per_minute + 120 + duration / 60 * 2)


def transcribe_sources(sources: list[Source], major: str | None, materials: list, on_stage=None):
    """Join the recordings and transcribe them: (segments, duration, parts)."""
    stage = on_stage or (lambda *_: None)
    for s in sources:
        s.duration = s.duration or probe_duration(s.path)
    if sum(s.duration for s in sources) > config.MAX_LECTURE_MINUTES * 60:
        raise LectureTooLong()
    clips, parts, offset = [], [], 0.0
    for s in sources:
        clip = load_audio(s.path)
        parts.append((offset, s.title))
        clips.append(clip)
        offset += len(clip) / SAMPLE_RATE
    audio = np.concatenate(clips) if len(clips) > 1 else clips[0]
    del clips
    duration = len(audio) / SAMPLE_RATE
    terms = materials_mod.key_terms([m.text for m in materials])
    stage("transcribe", 0.0)
    segments = transcribe.transcribe(audio, major, on_progress=lambda f: stage("transcribe", f), terms=terms)
    return segments, duration, parts


def finish(result: dict, segments: list, out_dir: Path, source: Source, duration: float, name_suffix: str = "",
           on_stage=None) -> LectureResult:
    """Apply the transcript fixes, render the PDF."""
    (on_stage or (lambda *_: None))("render", 0.0)
    segments = analyze.apply_fixes(segments, result.get("transcript_fixes", []))
    paragraphs = transcribe.to_paragraphs(segments)
    files = write_files(result, paragraphs, out_dir, source.title, source.url, duration, name_suffix)
    text = render.transcript_txt(paragraphs) if paragraphs else ""
    return LectureResult(result, paragraphs, files["summary"], text, source, extra={"duration": duration, "files": files})


def write_files(result: dict, paragraphs: list, out_dir: Path, source_title: str = "", source_url: str = "",
                duration: float = 0.0, name_suffix: str = "") -> dict:
    """The lecture's PDFs (summary, questions, glossary, illustrations): kind -> path."""
    title = safe_name(result.get("title") or source_title)
    names = dict(render.FILES)
    return {kind: render.write_pdf(html, out_dir / f"{names[kind]} - {title}{name_suffix}.pdf")
            for kind, html in render.build_files(result, paragraphs, source_title, source_url, duration).items()}


def paragraphs_of(transcript: str) -> list:
    """The stored transcript ("[mm:ss] text" paragraphs) back as segments."""
    out = []
    for para in (transcript or "").split("\n\n"):
        if para.startswith("[") and "]" in para:
            start = parse_time(para[1:para.index("]")]) or 0.0
            out.append(transcribe.Segment(start, start, para[para.index("]") + 1:].strip()))
    return out


def run(source: Source | list[Source], out_dir: Path, major: str | None = None,
        images: list[tuple[bytes, str]] | None = None, on_stage=None, analyzer=None,
        materials: list | None = None, on_section=None, model: str | None = None) -> LectureResult:
    """on_stage(stage, fraction) reports progress: stage is 'transcribe', 'analyze' or 'render'.
    Several sources are joined, in order, into one lecture."""
    stage = on_stage or (lambda *_: None)
    sources = source if isinstance(source, list) else [source]
    materials = materials or []
    segments, duration, parts = transcribe_sources(sources, major, materials, stage)
    stage("analyze", 0.0)
    if analyzer:
        result = analyzer(segments, major=major, images=images, duration=duration)
    else:
        result = analyze.analyze(segments, major=major, images=images, duration=duration, materials=materials,
                                 parts=parts, on_section=on_section, model=model,
                                 questions_model=config.QUESTIONS_MODEL)
    first = sources[0] if len(sources) == 1 else Source(path=sources[0].path, title="")
    return finish(result, segments, out_dir, first, duration, on_stage=stage)


def run_files(out_dir: Path, title: str, major: str | None = None, images: list[tuple[bytes, str]] | None = None,
              materials: list | None = None, on_stage=None, on_section=None, model: str | None = None) -> LectureResult:
    """A lecture with no recording: summarise the slides, files or photos of book pages alone."""
    stage = on_stage or (lambda *_: None)
    materials = materials or []
    stage("analyze", 0.0)
    result = analyze.analyze([], major=major, images=images, materials=materials, on_section=on_section, model=model,
                             questions_model=config.QUESTIONS_MODEL)
    res = finish(result, [], out_dir, Source(path=Path(title or "lecture"), title=title), 0.0, on_stage=stage)
    # The files' text stands in for the transcript (search and explanations use it).
    res.transcript_text = "\n\n".join(m.text for m in materials if m.text)
    return res
