import shutil
from pathlib import Path

import database
from config import RECORDINGS_DIR, SYNCED_DIR
from database import Recording


def disk_free_gb(path: Path = RECORDINGS_DIR) -> float:
    try:
        usage = shutil.disk_usage(str(path))
        return usage.free / (1024 ** 3)
    except Exception:
        return 0.0


def move_to_synced(rec: Recording) -> None:
    audio_src = Path(rec.audio_path)
    if audio_src.exists():
        audio_dst = SYNCED_DIR / f"{rec.filename}.wav"
        try:
            shutil.move(str(audio_src), str(audio_dst))
            database.update_audio_path(rec.id, str(audio_dst))
        except Exception:
            pass

    if rec.transcript_path:
        transcript_src = Path(rec.transcript_path)
        if transcript_src.exists():
            transcript_dst = SYNCED_DIR / f"{rec.filename}.txt"
            try:
                shutil.move(str(transcript_src), str(transcript_dst))
                database.update_transcript_path(rec.id, str(transcript_dst))
            except Exception:
                pass


def delete_recording_files(rec: Recording) -> None:
    for path_str in (rec.audio_path, rec.transcript_path):
        if not path_str:
            continue
        path = Path(path_str)
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass
