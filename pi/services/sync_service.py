from pathlib import Path

import requests

from config import ALLY_SYNC_TIMEOUT_SECONDS, ALLY_URL
from database import Recording


def sync_one(rec: Recording) -> tuple[bool, str]:
    audio_path = Path(rec.audio_path)
    transcript_path = Path(rec.transcript_path) if rec.transcript_path else None

    if transcript_path is None or not transcript_path.exists():
        transcript_path = audio_path.with_suffix(".txt")
        try:
            transcript_path.write_text("", encoding="utf-8")
        except Exception:
            pass

    audio_fh = None
    transcript_fh = None
    try:
        audio_fh = audio_path.open("rb")
        transcript_fh = transcript_path.open("rb")
        files = {
            "audio_file": (audio_path.name, audio_fh, "audio/wav"),
            "transcript_file": (transcript_path.name, transcript_fh, "text/plain"),
        }
        data = {
            "filename": rec.filename,
            "duration_seconds": str(rec.duration_seconds),
            "label": rec.label or rec.filename,
        }
        response = requests.post(
            f"{ALLY_URL}/sync",
            files=files,
            data=data,
            timeout=ALLY_SYNC_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return True, "sent"
        return False, f"HTTP {response.status_code}"
    except requests.ConnectionError:
        return False, "Could not reach the Ally"
    except requests.Timeout:
        return False, "Timed out"
    except Exception as exc:
        return False, str(exc)[:80]
    finally:
        if audio_fh:
            audio_fh.close()
        if transcript_fh:
            transcript_fh.close()
