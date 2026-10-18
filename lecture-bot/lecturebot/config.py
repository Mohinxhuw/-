"""Settings read from environment variables (see .env.example)."""
import os
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


BASE_DIR = Path(__file__).resolve().parent.parent

try:  # read .env when running outside Docker
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Optional self-hosted Telegram Bot API server (lifts the 20 MB download limit to 2 GB).
# Example: http://telegram-bot-api:8081
TELEGRAM_LOCAL_API_URL = os.environ.get("TELEGRAM_LOCAL_API_URL", "").rstrip("/")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.environ.get("CLAUDE_EFFORT", "medium")

# Fast transcription service (Groq). When a key is set it is used first, with the local model as fallback.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "whisper-large-v3")  # the full model: best accuracy for Arabic
GROQ_PARALLEL = int(os.environ.get("GROQ_PARALLEL", "4"))
TRANSCRIBE_CHUNK_SECONDS = int(os.environ.get("TRANSCRIBE_CHUNK_SECONDS", "600"))

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_THREADS = int(os.environ.get("WHISPER_THREADS", "4"))
# Batched decoding is faster on long recordings with the same accuracy; 1 turns it off.
WHISPER_BATCH_SIZE = int(os.environ.get("WHISPER_BATCH_SIZE", "8"))
# Rough processing time per minute of audio, used only for the ETA shown to students.
WHISPER_SECONDS_PER_AUDIO_MINUTE = float(os.environ.get("WHISPER_SECONDS_PER_AUDIO_MINUTE", "28"))
GROQ_SECONDS_PER_AUDIO_MINUTE = 2.0

# Lectures processed at the same time. Local transcription uses the whole CPU, so one at a time.
MAX_PARALLEL_JOBS = int(os.environ.get("MAX_PARALLEL_JOBS", "3" if GROQ_API_KEY else "1"))

MAX_LECTURE_MINUTES = int(os.environ.get("MAX_LECTURE_MINUTES", "240"))
MAX_IMAGES_PER_LECTURE = int(os.environ.get("MAX_IMAGES_PER_LECTURE", "20"))
MAX_DOCUMENTS_PER_LECTURE = int(os.environ.get("MAX_DOCUMENTS_PER_LECTURE", "3"))
MAX_DOCUMENT_MB = int(os.environ.get("MAX_DOCUMENT_MB", "30"))
# After a recording arrives the bot waits this long for more parts before it starts.
PARTS_WAIT_SECONDS = int(os.environ.get("PARTS_WAIT_SECONDS", "40"))
MAX_PARTS = int(os.environ.get("MAX_PARTS", "8"))
# Photos sent before a lecture are attached to it if they are newer than this.
PENDING_IMAGES_TTL_MINUTES = int(os.environ.get("PENDING_IMAGES_TTL_MINUTES", "120"))

# Lectures kept per student (for the study buttons, questions and the exam-night summary).
KEEP_LECTURES = int(os.environ.get("KEEP_LECTURES", "30"))
# Daily review reminder: students' time zone and the default hour (24h); /reminder changes it.
REMINDER_TZ = os.environ.get("REMINDER_TZ", "Asia/Riyadh")
DEFAULT_REMINDER_HOUR = int(os.environ.get("DEFAULT_REMINDER_HOUR", "20"))
REVIEW_CARDS_PER_DAY = int(os.environ.get("REVIEW_CARDS_PER_DAY", "25"))

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/lecturebot"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
FONTS_DIR = BASE_DIR / "fonts"

DEBUG = _bool("DEBUG")
