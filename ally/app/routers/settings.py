"""Settings + system stats endpoints."""

import importlib.metadata
import os
import sys
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Note, get_db
from settings_store import (
    DEFAULTS,
    get_ollama_endpoint,
    load_settings,
    save_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])

DATABASE_FILE = "database.db"


class SettingsUpdate(BaseModel):
    ollama_endpoint: Optional[str] = None
    audio_storage_path: Optional[str] = None
    transcript_storage_path: Optional[str] = None


def _is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _dir_size_bytes(path: str) -> int:
    if not path or not os.path.isdir(path):
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            full = os.path.join(root, name)
            try:
                total += os.path.getsize(full)
            except OSError:
                continue
    return total


def _file_size_bytes(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _bytes_to_mb(n: int) -> float:
    return round(n / (1024 * 1024), 2)


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _python_version() -> str:
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"


def _build_response(db: Session) -> dict:
    settings = load_settings()
    last_synced = db.query(func.max(Note.created_at)).scalar()
    total_notes = db.query(func.count(Note.id)).scalar() or 0

    return {
        **settings,
        "audio_size_mb": _bytes_to_mb(_dir_size_bytes(settings["audio_storage_path"])),
        "transcript_size_mb": _bytes_to_mb(
            _dir_size_bytes(settings["transcript_storage_path"])
        ),
        "database_size_mb": _bytes_to_mb(_file_size_bytes(DATABASE_FILE)),
        "total_notes": total_notes,
        "last_synced_at": last_synced.isoformat() if last_synced else None,
        "python_version": _python_version(),
        "fastapi_version": _package_version("fastapi"),
    }


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    return _build_response(db)


@router.put("")
def put_settings(body: SettingsUpdate, db: Session = Depends(get_db)):
    if body.ollama_endpoint is not None and not _is_valid_url(body.ollama_endpoint):
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid URL (e.g. http://localhost:11434)",
        )
    for label, candidate in (
        ("audio_storage_path", body.audio_storage_path),
        ("transcript_storage_path", body.transcript_storage_path),
    ):
        if candidate is not None and not os.path.isdir(candidate):
            raise HTTPException(
                status_code=400,
                detail="Path not found on disk. Create it first or check the spelling.",
            )

    save_settings(body.model_dump(exclude_none=True))
    return _build_response(db)


@router.post("/purge-done")
def purge_done(db: Session = Depends(get_db)):
    settings = load_settings()
    transcript_dir = settings["transcript_storage_path"]

    done_notes = db.query(Note).filter(Note.status == "done").all()
    if not done_notes:
        return {"purged_count": 0, "space_reclaimed_mb": 0}

    reclaimed = 0
    purged = 0
    for note in done_notes:
        for path in (
            note.audio_path,
            os.path.join(transcript_dir, f"{note.filename}.txt"),
        ):
            if not path or not os.path.exists(path):
                continue
            reclaimed += _file_size_bytes(path)
            try:
                os.remove(path)
            except OSError:
                continue
        purged += 1

    return {
        "purged_count": purged,
        "space_reclaimed_mb": _bytes_to_mb(reclaimed),
    }


@router.get("/ollama-ping")
async def ollama_ping():
    """Optional probe used by the UI to surface a 'cannot reach Ollama' message."""
    endpoint = get_ollama_endpoint()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{endpoint}/api/tags")
            response.raise_for_status()
        return {"reachable": True}
    except (httpx.HTTPError, httpx.RequestError):
        return {"reachable": False}
