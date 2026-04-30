import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import Note, Template, get_db
from models import NoteDetail, NoteListItem, ReprocessRequest, StatusUpdate
from ollama_service import run_ollama

router = APIRouter(prefix="/notes", tags=["notes"])

TRANSCRIPT_DIR = os.path.join("storage", "transcripts")
PREVIEW_LEN = 120


def _list_item(note: Note) -> dict:
    return {
        "id": note.id,
        "filename": note.filename,
        "label": note.label or note.filename,
        "recorded_at": note.recorded_at,
        "duration_seconds": note.duration_seconds or 0,
        "status": note.status,
        "template_id": note.template_id,
        "template_name": note.template.name if note.template else None,
        "processed_note_preview": (note.processed_note or "")[:PREVIEW_LEN],
    }


def _detail(note: Note) -> dict:
    return {
        "id": note.id,
        "filename": note.filename,
        "label": note.label or note.filename,
        "recorded_at": note.recorded_at,
        "duration_seconds": note.duration_seconds or 0,
        "raw_transcript": note.raw_transcript or "",
        "processed_note": note.processed_note or "",
        "status": note.status,
        "template_id": note.template_id,
        "template_name": note.template.name if note.template else None,
        "created_at": note.created_at,
        "processed_at": note.processed_at,
    }


def _get_note_or_404(db: Session, note_id: int) -> Note:
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.get("", response_model=list[NoteListItem])
def list_notes(db: Session = Depends(get_db)):
    notes = (
        db.query(Note)
        .order_by(Note.recorded_at.is_(None), Note.recorded_at.desc())
        .all()
    )
    return [_list_item(n) for n in notes]


@router.get("/{note_id}", response_model=NoteDetail)
def get_note(note_id: int, db: Session = Depends(get_db)):
    return _detail(_get_note_or_404(db, note_id))


@router.patch("/{note_id}/status", response_model=NoteDetail)
def update_status(note_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    note = _get_note_or_404(db, note_id)
    note.status = body.status
    if body.status == "done":
        note.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return _detail(note)


@router.delete("/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = _get_note_or_404(db, note_id)
    _safe_unlink(note.audio_path)
    _safe_unlink(os.path.join(TRANSCRIPT_DIR, f"{note.filename}.txt"))
    db.delete(note)
    db.commit()
    return {"deleted": True}


@router.get("/{note_id}/audio")
def get_audio(note_id: int, db: Session = Depends(get_db)):
    note = _get_note_or_404(db, note_id)
    if not note.audio_path or not os.path.exists(note.audio_path):
        raise HTTPException(status_code=404, detail="Audio file missing")
    return FileResponse(note.audio_path, media_type="audio/wav")


@router.post("/{note_id}/reprocess", response_model=NoteDetail)
async def reprocess(
    note_id: int,
    body: ReprocessRequest,
    db: Session = Depends(get_db),
):
    note = _get_note_or_404(db, note_id)
    template = db.query(Template).filter(Template.id == body.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    note.status = "processing"
    db.commit()

    try:
        processed = await run_ollama(note.raw_transcript or "", template.template_text)
    except Exception as exc:
        note.status = "unsynced"
        db.commit()
        raise HTTPException(status_code=502, detail=f"Ollama failed: {exc}") from exc

    note.processed_note = processed
    note.template_id = template.id
    note.status = "ready"
    note.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return _detail(note)


def _safe_unlink(path: Optional[str]) -> None:
    if not path:
        return
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
