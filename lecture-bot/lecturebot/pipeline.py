"""The full lecture job: audio -> transcript -> study material -> PDF."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import analyze, config, materials as materials_mod, render, transcribe
from .media import SAMPLE_RATE, Source, load_audio, probe_duration


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


def run(source: Source | list[Source], out_dir: Path, major: str | None = None,
        images: list[tuple[bytes, str]] | None = None, on_stage=None, analyzer=None,
        materials: list | None = None, on_section=None) -> LectureResult:
    """on_stage(stage, fraction) reports progress: stage is 'transcribe', 'analyze' or 'render'.
    Several sources are joined, in order, into one lecture."""
    stage = on_stage or (lambda *_: None)
    sources = source if isinstance(source, list) else [source]
    for s in sources:
        s.duration = s.duration or probe_duration(s.path)
    total = sum(s.duration for s in sources)
    if total > config.MAX_LECTURE_MINUTES * 60:
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

    materials = materials or []
    terms = materials_mod.key_terms([m.text for m in materials])
    stage("transcribe", 0.0)
    segments = transcribe.transcribe(audio, major, on_progress=lambda f: stage("transcribe", f), terms=terms)
    del audio

    stage("analyze", 0.0)
    if analyzer:
        result = analyzer(segments, major=major, images=images, duration=duration)
    else:
        result = analyze.analyze(segments, major=major, images=images, duration=duration, materials=materials,
                                 parts=parts, on_section=on_section)
    segments = analyze.apply_fixes(segments, result.get("transcript_fixes", []))
    paragraphs = transcribe.to_paragraphs(segments)

    stage("render", 0.0)
    first = sources[0]
    title = first.title if len(sources) == 1 else ""
    html = render.build_html(result, paragraphs, title, first.url if len(sources) == 1 else "", duration)
    pdf = render.write_pdf(html, out_dir / f"{safe_name(result.get('title') or first.title)}.pdf")
    return LectureResult(result, paragraphs, pdf, render.transcript_txt(paragraphs), first,
                         extra={"duration": duration})
