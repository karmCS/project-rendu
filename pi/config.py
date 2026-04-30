import os
import platform
from pathlib import Path

IS_LINUX = platform.system() == "Linux"
DEV_MODE = (not IS_LINUX) or os.environ.get("RENDU_DEV") == "1"

PROJECT_ROOT = Path(__file__).parent

_ALLY_HOST = os.environ.get("RENDU_ALLY_HOST", "rendu-ally")
_ALLY_URL_OVERRIDE = os.environ.get("RENDU_ALLY_URL")

if DEV_MODE:
    RECORDINGS_DIR = PROJECT_ROOT / "recordings"
    DB_PATH = PROJECT_ROOT / "database.db"
    ALLY_URL = _ALLY_URL_OVERRIDE or "http://localhost:8000"
else:
    RECORDINGS_DIR = Path("/home/pi/rendu-pi/recordings")
    DB_PATH = Path("/home/pi/rendu-pi/database.db")
    ALLY_URL = _ALLY_URL_OVERRIDE or f"http://{_ALLY_HOST}.local:8000"

UNSYNCED_DIR = RECORDINGS_DIR / "unsynced"
SYNCED_DIR = RECORDINGS_DIR / "synced"

WHISPER_BIN = "/usr/local/bin/whisper-cpp"
WHISPER_MODEL = "/home/pi/models/ggml-small.bin"
WHISPER_TIMEOUT_SECONDS = 600
WHISPER_MOCK_DELAY_SECONDS = 3.0
WHISPER_MOCK_TEXT = (
    "Patient presents for a follow-up visit regarding hypertension management. "
    "Blood pressure readings have been well-controlled on the current medication regimen. "
    "Patient denies any chest pain, shortness of breath, or headaches. "
    "Continue current antihypertensive therapy. Follow up in three months."
)

ALLY_SYNC_TIMEOUT_SECONDS = 60

IDLE_TIMEOUT_SECONDS = 900

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_WIDTH = 2
AUDIO_FRAMES_PER_BUFFER = 1024
WAVEFORM_UPDATE_MS = 100

WINDOW_SIZE = (800, 480)
TAB_BAR_HEIGHT = 72

COLOR_BG = "#1a1a1a"
COLOR_CARD = "#2a2a2a"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_MUTED = "#888888"
COLOR_RECORD = "#cc3333"
COLOR_STOP = "#444444"
COLOR_PAUSE = "#e6a817"
COLOR_SYNC = "#2d6bbf"
COLOR_TAB_BG = "#111111"
COLOR_TAB_ACTIVE = "#ffffff"
COLOR_TAB_INACTIVE = "#555555"
COLOR_WAVEFORM = "#7298C7"
COLOR_GREEN = "#4caf50"
COLOR_RED = "#f44336"

STATUS_TRANSCRIBING = "transcribing"
STATUS_UNSYNCED = "unsynced"
STATUS_SYNCING = "syncing"
STATUS_SYNCED = "synced"
STATUS_SYNC_FAILED = "sync_failed"

for _d in (UNSYNCED_DIR, SYNCED_DIR, DB_PATH.parent):
    _d.mkdir(parents=True, exist_ok=True)
