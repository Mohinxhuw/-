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

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_THREADS = int(os.environ.get("WHISPER_THREADS", "4"))
# Rough processing time per minute of audio, used only for the ETA shown to students.
WHISPER_SECONDS_PER_AUDIO_MINUTE = float(os.environ.get("WHISPER_SECONDS_PER_AUDIO_MINUTE", "35"))

MAX_LECTURE_MINUTES = int(os.environ.get("MAX_LECTURE_MINUTES", "150"))
MAX_IMAGES_PER_LECTURE = int(os.environ.get("MAX_IMAGES_PER_LECTURE", "20"))
# Photos sent before a lecture are attached to it if they are newer than this.
PENDING_IMAGES_TTL_MINUTES = int(os.environ.get("PENDING_IMAGES_TTL_MINUTES", "120"))

WORK_DIR = Path(os.environ.get("WORK_DIR", "/tmp/lecturebot"))
DATA_DIR = Path(os.environ.get("DATA_DIR", str(BASE_DIR / "data")))
FONTS_DIR = BASE_DIR / "fonts"

DEBUG = _bool("DEBUG")
