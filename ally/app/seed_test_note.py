"""Drop a fake note into the running backend so the kanban has something to chew on.

Run from the app/ directory while uvicorn is up:
    python seed_test_note.py

Optional flags:
    --base http://localhost:8000    Backend URL
    --transcript "..."              Custom transcript text
    --duration 12                   Duration in seconds (just a label)
"""

from __future__ import annotations

import argparse
import struct
import sys
from datetime import datetime
from pathlib import Path

import httpx

DEFAULT_TRANSCRIPT = (
    "Patient Jane Doe, DOB 03/14/1972, MRN 99887, presents for follow-up. "
    "Reports two weeks of intermittent lower back pain, worse with prolonged sitting, "
    "no radiation, no numbness or weakness. Denies fever, weight loss, or bowel/bladder changes. "
    "Tried over-the-counter ibuprofen with partial relief. "
    "On exam: tenderness over L4-L5 paraspinal muscles, full range of motion, neuro intact. "
    "Plan: continue ibuprofen 600mg TID with food, stretching exercises, "
    "follow up in two weeks if no improvement. Return precautions discussed."
)


def make_silent_wav(seconds: float = 2.0, sample_rate: int = 8000) -> bytes:
    n_samples = max(1, int(seconds * sample_rate))
    pcm = b"\x00\x00" * n_samples
    byte_rate = sample_rate * 2
    block_align = 2
    data_size = len(pcm)
    riff_size = 36 + data_size
    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    fmt = b"fmt " + struct.pack(
        "<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, block_align, 16
    )
    data = b"data" + struct.pack("<I", data_size) + pcm
    return header + fmt + data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--transcript", default=DEFAULT_TRANSCRIPT)
    parser.add_argument("--duration", type=int, default=12)
    parser.add_argument(
        "--filename",
        default=None,
        help="Override the recording filename (default: now in YYYY-MM-DD_HH-MM-SS).",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="User-typed label for the recording (default: filename timestamp).",
    )
    args = parser.parse_args()

    filename = args.filename or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    wav_bytes = make_silent_wav(seconds=2.0)
    transcript_bytes = args.transcript.encode("utf-8")

    print(f"  base:       {args.base}")
    print(f"  filename:   {filename}")
    print(f"  duration:   {args.duration}s")
    print(f"  transcript: {len(transcript_bytes)} bytes")
    print(f"  audio:      {len(wav_bytes)} bytes (silent test wav)")
    print()

    files = {
        "audio_file": (f"{filename}.wav", wav_bytes, "audio/wav"),
        "transcript_file": (f"{filename}.txt", transcript_bytes, "text/plain"),
    }
    data = {"filename": filename, "duration_seconds": str(args.duration)}
    if args.label:
        data["label"] = args.label

    try:
        resp = httpx.post(f"{args.base}/sync", files=files, data=data, timeout=30.0)
    except httpx.RequestError as exc:
        print(f"  ERROR: could not reach backend at {args.base}")
        print(f"         {exc}")
        return 1

    if resp.status_code != 200:
        print(f"  ERROR: backend returned HTTP {resp.status_code}")
        print(f"         {resp.text[:500]}")
        return 1

    payload = resp.json()
    print(f"  OK: created note id={payload['id']} status={payload['status']}")
    print()
    print("  Open http://localhost:8000/ in your browser.")
    print("  The card will appear in 'Processing' and flip to 'Ready to Review'")
    print("  once Ollama finishes (~10-30s on phi3:mini cold start).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
