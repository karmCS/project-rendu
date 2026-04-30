# Rendu - Backend Spec for Claude Code

## What You're Building

A FastAPI backend that runs on an ASUS ROG Ally (Windows). It receives audio + transcript files from a Raspberry Pi over the local network, runs them through Ollama for PHI redaction and formatting, stores results in SQLite, and serves a React frontend as static files.

No cloud. No external APIs. Everything is local.

---

## Project Structure

```
app/
  main.py               # FastAPI app entry point
  database.py           # SQLAlchemy setup and models
  models.py             # Pydantic schemas
  ollama_service.py     # Ollama interaction
  routers/
    notes.py
    templates.py
    sync.py
  static/               # React build output (drop here after Claude Design export)
  storage/
    audio/
    transcripts/
  database.db           # Auto-created on first run
```

---

## Tech Stack

- **FastAPI** - API framework
- **SQLAlchemy** + **SQLite** - database (single file, `database.db`)
- **httpx** or **requests** - call Ollama's local REST API
- **python-multipart** - for file upload handling in `/sync`
- **uvicorn** - ASGI server

Install: `pip install fastapi uvicorn sqlalchemy python-multipart httpx`

---

## Auto-Start (Windows)

Use Windows Task Scheduler:
- Trigger: On system startup
- Action: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Working directory: the `app/` folder

---

## CORS

Enable CORS for all origins (local network use only, no auth needed):

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

---

## Serving the React Frontend

Mount the `static/` folder so the React build is accessible at the root:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

API routes must be registered **before** the static mount or they'll be shadowed.

---

## Ollama Integration

Ollama runs locally on the Ally. Call it via its REST API:

```
POST http://localhost:11434/api/generate
```

```python
import httpx

async def run_ollama(transcript: str, template_text: str) -> str:
    prompt = f"""You are a clinical documentation assistant.

Redact any patient identifiers (name, DOB, MRN, address, phone number, insurance ID)
and reformat the following transcript into the structure below.

Template:
{template_text}

Transcript:
{transcript}

Return only the formatted note. No explanation, no preamble."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3:8b", "prompt": prompt, "stream": False}
        )
        return response.json()["response"]
```

Model: `llama3:8b`. Must be pulled first: `ollama pull llama3:8b`

---

## First-Run Seed

On startup, check if the templates table is empty. If so, insert the four default templates:

1. **Epic Follow Up** (`epic`)
2. **Epic New Patient** (`epic`)  
3. **SOAP Note** (`soap`)
4. **DAP Note** (`dap`)

Mark "SOAP Note" as `is_default = True`.

Template text content is in `rendu_data_model.md`.
