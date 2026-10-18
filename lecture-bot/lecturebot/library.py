"""A student's library: courses (folders), search across lectures, exam dates and study plans.
Pure functions over the student's data, so they are easy to test."""
import datetime as dt
import math
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


# ---------- exam dates and study plans ----------

def parse_date(text: str, today: dt.date) -> dt.date | None:
    """'2026-11-20', '20/11/2026', '20/11', 'بعد 10 أيام', 'غداً'. Day/month order as used in Arabic."""
    t = normalize(text)
    if t in ("غدا", "بكره", "بكرة"):
        return today + dt.timedelta(days=1)
    if t in ("بعد غد", "بعد بكره"):
        return today + dt.timedelta(days=2)
    m = re.search(r"بعد\s+(\d+)\s*(يوم|ايام|اسبوع|اسابيع)", t)
    if m:
        n = int(m.group(1))
        return today + dt.timedelta(days=n * (7 if m.group(2).startswith("اس") else 1))
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    try:
        if m:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.search(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", t)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            year = int(m.group(3)) if m.group(3) else today.year
            year += 2000 if year < 100 else 0
            d = dt.date(year, month, day)
            if not m.group(3) and d < today:  # "20/1" in December means next January
                d = dt.date(year + 1, month, day)
            return d
    except ValueError:
        return None
    return None


def days_left(course: dict, today: dt.date) -> int | None:
    if not course.get("exam"):
        return None
    return (dt.date.fromisoformat(course["exam"]) - today).days


def make_plan(lecture_ids: list[str], exam: dt.date, today: dt.date) -> list[dict]:
    """Spread the course's lectures over the days before the exam; the day before is for a full review."""
    days = (exam - today).days
    if days <= 1 or not lecture_ids:
        return [{"date": today.isoformat(), "lids": list(lecture_ids), "review": True, "done": False}]
    study_days = days - 1
    per_day = max(1, math.ceil(len(lecture_ids) / study_days))
    chunks = [lecture_ids[i:i + per_day] for i in range(0, len(lecture_ids), per_day)]
    # Spread the study days evenly, leaving rest days in between when there is time to spare.
    plan = [{"date": (today + dt.timedelta(days=j * study_days // len(chunks))).isoformat(), "lids": chunk,
             "review": False, "done": False} for j, chunk in enumerate(chunks)]
    plan.append({"date": (exam - dt.timedelta(days=1)).isoformat(), "lids": [], "review": True, "done": False})
    return plan


def today_tasks(ud: dict, today: dt.date) -> list[tuple[str, int, dict]]:
    """(course id, index in plan, plan day) for every plan day due today or overdue and not done."""
    out = []
    t = today.isoformat()
    for cid, c in courses(ud).items():
        if c.get("exam") and c["exam"] < t:
            continue  # the exam has passed
        for i, day in enumerate(c.get("plan", [])):
            if day["date"] <= t and not day["done"]:
                out.append((cid, i, day))
    return out


def day_name(d: dt.date, today: dt.date) -> str:
    if d == today:
        return "اليوم"
    if d == today + dt.timedelta(days=1):
        return "غداً"
    return f"{WEEKDAYS[d.weekday()]} {d.day}/{d.month}"


def countdown_text(n: int) -> str:
    if n == 0:
        return "الاختبار اليوم"
    if n == 1:
        return "الاختبار غداً"
    if n == 2:
        return "باقي يومان"
    return f"باقي {n} " + ("أيام" if n <= 10 else "يوماً")
