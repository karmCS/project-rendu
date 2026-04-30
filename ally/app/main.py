import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers.notes import router as notes_router
from routers.settings import router as settings_router
from routers.sync import router as sync_router
from routers.templates import router as templates_router
from seed import seed_templates

app = FastAPI(title="Rendu API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    os.makedirs("storage/audio", exist_ok=True)
    os.makedirs("storage/transcripts", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    init_db()
    seed_templates()


@app.get("/health", tags=["meta"])
def health():
    return {"ok": True}


# API routes must be registered BEFORE the static mount or they'll be shadowed.
app.include_router(sync_router)
app.include_router(notes_router)
app.include_router(templates_router)
app.include_router(settings_router)


# Only mount static if a built React app is present (index.html exists),
# otherwise the empty mount swallows /docs.
_static_dir = os.environ.get("RENDU_STATIC_DIR", "static")
_static_index = os.path.join(_static_dir, "index.html")
if os.path.isfile(_static_index):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
