"""A student's library: courses (folders) and search across lectures.
Pure functions over the student's data, so they are easy to test."""
import datetime as dt
import re
import uuid

from . import store

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def normalize(text: str) -> str:
    """For matching Arabic: drop diacritics and tatweel, unify alef, ya and ta marbuta forms, lower-case."""
    t = _DIACRITICS.sub("", text or "").translate(_ARABIC_DIGITS)
    t = re.sub("[إأآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return re.sub(r"\s+", " ", t).strip().lower()


# ---------- courses ----------

def courses(ud: dict) -> dict:
    return ud.setdefault("courses", {})


def new_course(ud: dict, name: str) -> str:
    cid = uuid.uuid4().hex[:6]
    courses(ud)[cid] = {"name": name.strip()[:60] or "مادة", "exam": None, "plan": []}
    return cid


def find_course(ud: dict, subject: str) -> str | None:
    """The course whose name matches the subject Claude gave the lecture, if any."""
    s = normalize(subject)
    if not s:
        return None
    for cid, c in courses(ud).items():
        n = normalize(c["name"])
        if n == s or (len(n) >= 4 and (n in s or s in n)):
            return cid
    # A course where an earlier lecture had the same subject.
    for lid, meta in ud.get("lectures", {}).items():
        if meta.get("course") in courses(ud) and normalize(meta.get("subject", "")) == s:
            return meta["course"]
    return None


def assign_course(ud: dict, lid: str, subject: str) -> str:
    cid = find_course(ud, subject) or new_course(ud, subject or "عام")
    ud["lectures"][lid]["course"] = cid
    return cid


def course_lectures(ud: dict, cid: str) -> list[str]:
    lectures = ud.get("lectures", {})
    return sorted((lid for lid, m in lectures.items() if m.get("course") == cid), key=lambda k: lectures[k]["time"])


def unfiled(ud: dict) -> list[str]:
    lectures, known = ud.get("lectures", {}), courses(ud)
    return sorted((lid for lid, m in lectures.items() if m.get("course") not in known),
                  key=lambda k: lectures[k]["time"])


# ---------- search ----------

def search(user_id: int, ud: dict, query: str, limit: int = 8) -> list[dict]:
    """Paragraphs of the student's lectures that contain all the words of the query, best first."""
    words = [w for w in normalize(query).split() if len(w) > 1]
    if not words:
        return []
    hits = []
    for lid, meta in ud.get("lectures", {}).items():
        full = store.get(user_id, ud, lid)
        if not full:
            continue
        title_hit = all(w in normalize(meta.get("title", "")) for w in words)
        for line in (full.get("transcript") or "").split("\n\n"):
            m = re.match(r"\[(\d+(?::\d+)+)\]\s*(.*)", line, re.S)
            time, text = (m.group(1), m.group(2)) if m else ("", line)
            n = normalize(text)
            if all(w in n for w in words):
                score = sum(n.count(w) for w in words) + (3 if title_hit else 0)
                hits.append({"lid": lid, "title": meta.get("title", ""), "time": time,
                             "snippet": _snippet(text, words), "score": score})
    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]


def _snippet(text: str, words: list[str], width: int = 160) -> str:
    n = normalize(text)
    pos = min((n.find(w) for w in words if n.find(w) >= 0), default=0)
    # normalize() keeps text length close to the original except for removed diacritics; good enough
    start = max(0, pos - width // 3)
    piece = text[start:start + width].strip()
    return ("…" if start > 0 else "") + piece + ("…" if start + width < len(text) else "")


# ---------- dates ----------

def day_name(d: dt.date, today: dt.date) -> str:
    if d == today:
        return "اليوم"
    if d == today + dt.timedelta(days=1):
        return "غداً"
    return f"{WEEKDAYS[d.weekday()]} {d.day}/{d.month}"
