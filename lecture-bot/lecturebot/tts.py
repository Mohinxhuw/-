"""Text to speech for the audio summary, with Microsoft Edge's free online voices (edge-tts).
No key is needed. The voice is set by TTS_VOICE (for example ar-SA-ZariyahNeural for a female voice)."""
import asyncio
import subprocess
from pathlib import Path

from . import config


class TTSError(Exception):
    pass


def speak(text: str, out_path: Path) -> Path:
    """Write an MP3 of the text; returns its path. Raises TTSError if the voice service fails."""
    import edge_tts

    async def run():
        await edge_tts.Communicate(text, config.TTS_VOICE, rate=config.TTS_RATE).save(str(out_path))

    try:
        asyncio.run(run())
    except Exception as e:
        raise TTSError(str(e)) from e
    if not out_path.exists() or out_path.stat().st_size < 1000:
        raise TTSError("empty audio")
    return out_path


def duration(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return int(float(out))
    except ValueError:
        return 0
