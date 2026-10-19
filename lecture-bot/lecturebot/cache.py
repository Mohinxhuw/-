"""Lectures already processed, by recording: when another student sends the same recording (the same
Telegram file, or the same link), the stored result is reused instead of paying to process it again.

Telegram gives every file a file_unique_id that is the same for everyone who sends or forwards it,
so a repeat is recognised before anything is downloaded."""
import hashlib
import json
import re

from . import config

_YOUTUBE_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{6,})")
_DRIVE_ID = re.compile(r"(?:/d/|id=)([\w-]{10,})")


def _part_key(part: dict) -> str | None:
    if part.get("uid"):
        return "tg:" + part["uid"]
    url = part.get("url") or ""
    m = _YOUTUBE_ID.search(url) or _DRIVE_ID.search(url)
    return ("url:" + m.group(1)) if m else None


def key_for(parts: list[dict]) -> str | None:
    """One key for the whole set of recordings, or None if one of them cannot be identified."""
    keys = [_part_key(p) for p in parts]
    if not keys or None in keys:
        return None
    return hashlib.sha256("|".join(keys).encode()).hexdigest()[:32]


def _path(key: str):
    return config.DATA_DIR / "cache" / f"{key}.json"


def get(key: str | None) -> dict | None:
    if not key or not _path(key).exists():
        return None
    return json.loads(_path(key).read_text(encoding="utf-8"))


def put(key: str | None, full: dict) -> None:
    if not key:
        return
    path = _path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {k: v for k, v in full.items() if k not in ("course", "time", "shared_from", "en_file_id")}
    path.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
