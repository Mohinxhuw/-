"""Lectures on disk: one JSON file per lecture (transcript, notes, questions), per student.

The bot's state (user_data) keeps only light details of each lecture (title, course, date, the
Telegram file id of its PDF), so the state file stays small however many lectures a student has.
"""
import json
import shutil
from pathlib import Path

from . import config

META_KEYS = ("title", "subject", "course", "time", "duration", "pdf_file_id", "shared_from")


def _dir(user_id: int) -> Path:
    return config.DATA_DIR / "lectures" / str(int(user_id))


def save(user_id: int, lid: str, full: dict) -> None:
    d = _dir(user_id)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"{lid}.json.tmp"
    tmp.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / f"{lid}.json")


def load(user_id: int, lid: str) -> dict | None:
    path = _dir(user_id) / f"{lid}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete(user_id: int, lid: str) -> None:
    (_dir(user_id) / f"{lid}.json").unlink(missing_ok=True)


def delete_user(user_id: int) -> None:
    shutil.rmtree(_dir(user_id), ignore_errors=True)


def meta_of(full: dict) -> dict:
    return {k: full.get(k) for k in META_KEYS if full.get(k) is not None}


def get(user_id: int, ud: dict, lid: str) -> dict | None:
    """The full lecture (details + content), or None. Lectures saved by older versions of the bot
    lived entirely in user_data; they are moved to disk the first time they are opened."""
    meta = ud.get("lectures", {}).get(lid)
    if meta is None:
        return None
    if "transcript" in meta:  # old format: move the content to disk
        save(user_id, lid, meta)
        ud["lectures"][lid] = meta = meta_of(meta)
    full = load(user_id, lid)
    if full is None:
        return None
    full.update(meta)  # details such as the course can change after saving
    return full


def put(user_id: int, ud: dict, lid: str, full: dict) -> None:
    save(user_id, lid, full)
    ud.setdefault("lectures", {})[lid] = meta_of(full)


def remove(user_id: int, ud: dict, lid: str) -> None:
    ud.get("lectures", {}).pop(lid, None)
    delete(user_id, lid)
