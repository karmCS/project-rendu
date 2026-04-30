import os
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from database import Note, SessionLocal, Template, get_db
from models import SyncResponse
from ollama_service import run_ollama

router = APIRouter(tags=["sync"])

AUDIO_DIR = os.path.join("storage", "audio")
TRANSCRIPT_DIR = os.path.join("storage", "transcripts")

FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})$")


def _parse_recorded_at(filename: str) -> Optional[datetime]:
    match = FILENAME_RE.match(filename)
    if not match:
        return None
    try:
        parts = [int(x) for x in match.groups()]
        return datetime(*parts)
    except (TypeError, ValueError):
        return None


async def _process_in_background(note_id: int) -> None:
    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            return
        template = (
            db.query(Template).filter(Template.id == note.template_id).first()
            if note.template_id
            else None
        )
        if not template:
            note.status = "unsynced"
            db.commit()
            return
        try:
            processed = await run_ollama(
                note.raw_transcript or "",
                template.template_text,
            )
            note.processed_note = processed
            note.status = "ready"
            note.processed_at = datetime.utcnow()
        except Exception:
            note.status = "unsynced"
        db.commit()
    finally:
        db.close()


@router.post("/sync", response_model=SyncResponse)
async def sync_note(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    transcript_file: UploadFile = File(...),
    filename: str = Form(...),
    duration_seconds: int = Form(...),
    label: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    audio_path = os.path.abspath(os.path.join(AUDIO_DIR, f"{filename}.wav"))
    transcript_path = os.path.abspath(os.path.join(TRANSCRIPT_DIR, f"{filename}.txt"))

    audio_bytes = await audio_file.read()
    with open(audio_path, "wb") as fh:
        fh.write(audio_bytes)

    transcript_bytes = await transcript_file.read()
    transcript_text = transcript_bytes.decode("utf-8", errors="replace")
    with open(transcript_path, "w", encoding="utf-8") as fh:
        fh.write(transcript_text)

    default_template = (
        db.query(Template).filter(Template.is_default.is_(True)).first()
        or db.query(Template).first()
    )

    cleaned_label = (label or "").strip() or filename

    note = Note(
        filename=filename,
        label=cleaned_label,
        recorded_at=_parse_recorded_at(filename),
        duration_seconds=duration_seconds,
        raw_transcript=transcript_text,
        processed_note="",
        template_id=default_template.id if default_template else None,
        status="processing",
        audio_path=audio_path,
        created_at=datetime.utcnow(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    background_tasks.add_task(_process_in_background, note.id)

    return SyncResponse(id=note.id, status="processing")
