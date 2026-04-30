from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    format_type = Column(String, nullable=False)
    template_text = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    notes = relationship("Note", back_populates="template")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    label = Column(String, nullable=True)
    recorded_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    raw_transcript = Column(Text, default="", nullable=False)
    processed_note = Column(Text, default="", nullable=False)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    status = Column(String, default="unsynced", nullable=False)
    audio_path = Column(String, default="", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    template = relationship("Template", back_populates="notes")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_note_label_column()


def _ensure_note_label_column() -> None:
    inspector = inspect(engine)
    if "notes" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("notes")}
    if "label" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE notes ADD COLUMN label VARCHAR"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
