"""The full lecture job: audio -> transcript -> study material -> PDF."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import analyze, config, render, transcribe
from .media import Source, load_audio, probe_duration


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
    """ETA shown to the student: transcription time plus about two minutes of writing."""
    return int(duration / 60 * config.WHISPER_SECONDS_PER_AUDIO_MINUTE + 120)


def run(source: Source, out_dir: Path, major: str | None = None, images: list[tuple[bytes, str]] | None = None,
        on_stage=None, analyzer=None) -> LectureResult:
    """on_stage(stage, fraction) reports progress: stage is 'transcribe', 'analyze' or 'render'."""
    stage = on_stage or (lambda *_: None)
    if not source.duration:
        source.duration = probe_duration(source.path)
    if source.duration > config.MAX_LECTURE_MINUTES * 60:
        raise LectureTooLong()

    audio = load_audio(source.path)
    stage("transcribe", 0.0)
    segments = transcribe.transcribe(audio, major, on_progress=lambda f: stage("transcribe", f))
    del audio

    stage("analyze", 0.0)
    result = (analyzer or analyze.analyze)(segments, major=major, images=images, duration=source.duration)
    segments = analyze.apply_fixes(segments, result.get("transcript_fixes", []))
    paragraphs = transcribe.to_paragraphs(segments)

    stage("render", 0.0)
    html = render.build_html(result, paragraphs, source.title, source.url, source.duration)
    pdf = render.write_pdf(html, out_dir / f"{safe_name(result.get('title') or source.title)}.pdf")
    return LectureResult(result, paragraphs, pdf, render.transcript_txt(paragraphs), source)
