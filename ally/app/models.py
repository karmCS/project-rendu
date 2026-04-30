from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TemplateBase(BaseModel):
    name: str
    format_type: str
    template_text: str
    is_default: bool = False


class TemplateCreate(TemplateBase):
    pass


class TemplateOut(TemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class NoteListItem(BaseModel):
    id: int
    filename: str
    label: Optional[str]
    recorded_at: Optional[datetime]
    duration_seconds: int
    status: str
    template_id: Optional[int]
    template_name: Optional[str]
    processed_note_preview: Optional[str]


class NoteDetail(BaseModel):
    id: int
    filename: str
    label: Optional[str]
    recorded_at: Optional[datetime]
    duration_seconds: int
    raw_transcript: str
    processed_note: str
    status: str
    template_id: Optional[int]
    template_name: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class StatusUpdate(BaseModel):
    status: str


class ReprocessRequest(BaseModel):
    template_id: int


class SyncResponse(BaseModel):
    id: int
    status: str
