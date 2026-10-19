"""Getting audio out of whatever the student sends: files, voice notes, videos, YouTube links."""
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
YOUTUBE_RE = re.compile(r"(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/|live/)|youtu\.be/)[\w\-]+[^\s]*")
DRIVE_RE = re.compile(r"(https?://)?(drive|docs)\.google\.com/[^\s]+")


@dataclass
class Source:
    path: Path
    title: str = ""
    url: str = ""          # set for YouTube, used to make timestamps clickable
    duration: float = 0.0  # seconds


def find_youtube_url(text: str) -> str | None:
    m = YOUTUBE_RE.search(text or "")
    if not m:
        return None
    url = m.group(0)
    return url if url.startswith("http") else "https://" + url


def find_media_url(text: str) -> str | None:
    """A YouTube or Google Drive link in the message, if any."""
    url = find_youtube_url(text)
    if url:
        return url
    m = DRIVE_RE.search(text or "")
    if not m:
        return None
    url = m.group(0)
    return url if url.startswith("http") else "https://" + url


def is_youtube(url: str) -> bool:
    return bool(YOUTUBE_RE.search(url or ""))


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def download_url(url: str, out_dir: Path, name: str = "dl") -> Source:
    """Download a YouTube video's audio or a Google Drive file (the file must be shared by link)."""
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / f"{name}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
    }
    # YouTube asks servers to prove they are not a bot; a signed-in account's cookies answer that.
    if is_youtube(url) and youtube_cookies().exists():
        opts["cookiefile"] = str(youtube_cookies())
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    page = info.get("webpage_url", url)
    return Source(path=path, title=Path(info.get("title", "")).stem, url=page if is_youtube(page) else "",
                  duration=float(info.get("duration") or 0) or probe_duration(path))


download_youtube = download_url


def youtube_cookies() -> Path:
    """cookies.txt of a YouTube account (sent to the bot by its owner with /cookies)."""
    from . import config
    return config.DATA_DIR / "youtube_cookies.txt"


def load_audio(path: Path) -> np.ndarray:
    """Decode any audio/video file to 16 kHz mono float32 with ffmpeg."""
    pcm = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def fmt_time(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_time(text: str) -> int | None:
    """'12:34' or '1:02:03' -> seconds."""
    parts = (text or "").strip().split(":")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    total = 0
    for p in parts:
        total = total * 60 + int(p)
    return total


def timestamp_url(source_url: str, seconds: int | None) -> str | None:
    if not source_url or seconds is None:
        return None
    sep = "&" if "?" in source_url else "?"
    return f"{source_url}{sep}t={seconds}s"


LOGIN_COOKIES = {"LOGIN_INFO", "SID", "__Secure-1PSID", "__Secure-3PSID", "SAPISID"}


def parse_cookies(data: bytes) -> tuple[str | None, str]:
    """A cookies export (Netscape cookies.txt, or the JSON some browser add-ons write) as a Netscape
    cookies.txt for yt-dlp, or (None, why it cannot be used)."""
    text = data.decode("utf-8", "ignore").lstrip("\ufeff").replace("\r\n", "\n")
    rows = []
    if text.lstrip().startswith(("[", "{")):
        import json
        try:
            items = json.loads(text)
        except ValueError:
            items = []
        for c in items if isinstance(items, list) else items.get("cookies", []):
            if isinstance(c, dict) and c.get("name") and c.get("domain"):
                d = c["domain"]
                rows.append([d, "TRUE" if d.startswith(".") else "FALSE", c.get("path", "/"),
                             "TRUE" if c.get("secure") else "FALSE",
                             str(int(c.get("expirationDate") or c.get("expires") or 0)), c["name"], str(c.get("value", ""))])
    else:
        for line in text.split("\n"):
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            parts = line.split("\t")
            if not line.startswith("#") and len(parts) == 7:
                rows.append(parts)
    if not rows:
        return None, "empty"
    youtube = [r for r in rows if r[0].lstrip(".").endswith(("youtube.com", "google.com"))]
    if not youtube:
        return None, "other_site"
    if not {r[5] for r in youtube} & LOGIN_COOKIES:
        return None, "signed_out"
    lines = ["# Netscape HTTP Cookie File"] + ["\t".join(r) for r in youtube]
    return "\n".join(lines) + "\n", ""
