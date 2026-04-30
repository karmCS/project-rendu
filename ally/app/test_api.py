"""End-to-end smoke test for the Rendu API.

Run the server in one terminal:
    cd app
    MOCK_OLLAMA=true uvicorn main:app --reload

Then in another:
    python test_api.py

Exercises every endpoint and prints a pass/fail summary.
"""

from __future__ import annotations

import io
import os
import struct
import sys
import time
from datetime import datetime

import httpx

BASE_URL = os.getenv("RENDU_BASE_URL", "http://localhost:8000")


def make_fake_wav(duration_seconds: float = 1.0, sample_rate: int = 8000) -> bytes:
    """Generate a tiny valid silent .wav so range requests succeed in the browser."""
    n_samples = int(duration_seconds * sample_rate)
    pcm = b"\x00\x00" * n_samples  # 16-bit silence
    byte_rate = sample_rate * 2
    block_align = 2
    data_size = len(pcm)
    riff_size = 36 + data_size
    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, block_align, 16)
    data = b"data" + struct.pack("<I", data_size) + pcm
    return header + fmt + data


def step(name: str) -> None:
    print(f"\n--- {name} ---")


def main() -> int:
    client = httpx.Client(base_url=BASE_URL, timeout=180.0)
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if cond:
            print(f"  PASS: {msg}")
        else:
            print(f"  FAIL: {msg}")
            failures.append(msg)

    step("health")
    r = client.get("/health")
    check(r.status_code == 200 and r.json().get("ok") is True, "GET /health")

    step("templates seeded")
    r = client.get("/templates")
    templates = r.json()
    check(r.status_code == 200, "GET /templates 200")
    check(len(templates) >= 4, f"expected >=4 seeded templates, got {len(templates)}")
    names = {t["name"] for t in templates}
    check("SOAP Note" in names, "SOAP Note present")
    check(any(t["is_default"] for t in templates), "exactly one is_default exists")
    soap = next(t for t in templates if t["name"] == "SOAP Note")

    step("create custom template")
    r = client.post(
        "/templates",
        json={
            "name": "Test Template",
            "format_type": "custom",
            "template_text": "Header:\n\nBody:",
            "is_default": False,
        },
    )
    check(r.status_code == 200, "POST /templates 200")
    custom = r.json()

    step("update template (toggle default)")
    r = client.put(
        f"/templates/{custom['id']}",
        json={
            "name": "Test Template (renamed)",
            "format_type": "custom",
            "template_text": "Header:\n\nBody:",
            "is_default": True,
        },
    )
    updated = r.json()
    check(r.status_code == 200 and updated["is_default"] is True, "PUT flips is_default")
    r = client.get("/templates")
    defaults = [t for t in r.json() if t["is_default"]]
    check(len(defaults) == 1 and defaults[0]["id"] == custom["id"], "only one is_default after PUT")

    # restore SOAP as default for the sync test
    client.put(
        f"/templates/{soap['id']}",
        json={
            "name": soap["name"],
            "format_type": soap["format_type"],
            "template_text": soap["template_text"],
            "is_default": True,
        },
    )

    step("sync upload")
    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    transcript = (
        "Patient John Smith DOB 01/02/1980 MRN 12345 reports lower back pain "
        "for two weeks. Denies fever. On exam tenderness L4-L5. "
        "Plan: ibuprofen, follow up two weeks."
    )
    files = {
        "audio_file": (f"{filename}.wav", make_fake_wav(2.0), "audio/wav"),
        "transcript_file": (f"{filename}.txt", transcript.encode("utf-8"), "text/plain"),
    }
    data = {"filename": filename, "duration_seconds": "2"}
    r = client.post("/sync", files=files, data=data)
    check(r.status_code == 200, f"POST /sync 200 (got {r.status_code}: {r.text[:200]})")
    sync_resp = r.json()
    note_id = sync_resp["id"]
    check(sync_resp["status"] == "processing", "sync returns processing")

    step("poll for ready")
    poll_seconds = int(os.getenv("RENDU_POLL_SECONDS", "120"))
    ready = False
    deadline = time.time() + poll_seconds
    while time.time() < deadline:
        r = client.get(f"/notes/{note_id}")
        status = r.json().get("status") if r.status_code == 200 else None
        if status == "ready":
            ready = True
            break
        if status == "unsynced":
            print("  note flipped to unsynced — Ollama call failed; check server logs")
            break
        time.sleep(1.0)
    check(ready, f"note transitioned to ready within {poll_seconds}s")

    step("note detail")
    r = client.get(f"/notes/{note_id}")
    detail = r.json()
    check(detail["raw_transcript"] == transcript, "raw_transcript round-trip")
    check(len(detail["processed_note"]) > 0, "processed_note populated")
    check(detail["template_name"] == "SOAP Note", "default template applied")
    check(detail["recorded_at"] is not None, "recorded_at parsed from filename")

    step("note list + preview")
    r = client.get("/notes")
    listing = r.json()
    found = next((n for n in listing if n["id"] == note_id), None)
    check(found is not None, "note appears in /notes")
    if found:
        check(len(found["processed_note_preview"] or "") <= 120, "preview <=120 chars")

    step("audio stream")
    r = client.get(f"/notes/{note_id}/audio")
    check(
        r.status_code == 200 and r.headers.get("content-type", "").startswith("audio/wav"),
        "GET /notes/{id}/audio returns audio/wav",
    )
    check(r.content[:4] == b"RIFF", "audio body looks like a WAV")

    step("reprocess with different template")
    dap = next(t for t in client.get("/templates").json() if t["name"] == "DAP Note")
    r = client.post(f"/notes/{note_id}/reprocess", json={"template_id": dap["id"]})
    check(r.status_code == 200, f"POST reprocess 200 (got {r.status_code}: {r.text[:200]})")
    if r.status_code == 200:
        rp = r.json()
        check(rp["template_id"] == dap["id"], "reprocess swapped template_id")
        check(rp["status"] == "ready", "reprocess result is ready")

    step("mark done")
    r = client.patch(f"/notes/{note_id}/status", json={"status": "done"})
    check(r.status_code == 200 and r.json()["status"] == "done", "PATCH status=done")

    step("delete template")
    r = client.delete(f"/templates/{custom['id']}")
    check(r.status_code == 200 and r.json().get("deleted") is True, "DELETE custom template")

    step("delete note")
    r = client.delete(f"/notes/{note_id}")
    check(r.status_code == 200 and r.json().get("deleted") is True, "DELETE note")
    r = client.get(f"/notes/{note_id}")
    check(r.status_code == 404, "note 404 after delete")

    print("\n" + "=" * 50)
    if failures:
        print(f"FAILED ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
