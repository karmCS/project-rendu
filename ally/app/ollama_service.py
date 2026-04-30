import os

import httpx

from settings_store import get_ollama_endpoint

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
MOCK_OLLAMA = os.getenv("MOCK_OLLAMA", "false").lower() in ("1", "true", "yes")

PROMPT_TEMPLATE = """You are a clinical documentation assistant. Your only job is to
RESTRUCTURE the transcript below into the provided template. You are NOT a clinician
and you are NOT writing a note from scratch.

STRICT RULES — follow every one:

1. FAITHFULNESS. Use ONLY information present in the transcript. Do not add, infer,
   embellish, suggest, recommend, or speculate. No clinical reasoning, no differential
   diagnoses, no patient education, no follow-up advice, no "consider...", no "encourage...",
   no "monitor...", unless those exact ideas appear in the transcript.
2. NO INVENTION. Do not invent vitals, exam findings, medications, dosages, durations,
   plans, or assessments. If the transcript does not state it, it does not appear.
3. EMPTY SECTIONS. If the transcript contains no information for a section in the
   template, leave that section blank (just the header followed by a blank line). Do not
   write "N/A", "none reported", or fill it with plausible content.
4. PRESERVE WORDING. Stay close to the clinician's own phrasing. Light cleanup of filler
   words ("um", "uh", false starts) is fine. Do not rewrite the clinical substance.
5. REDACT IDENTIFIERS. Remove patient name, date of birth, MRN, address, phone number,
   email, and insurance ID. Replace each with [REDACTED]. Do not redact clinical content.
6. OUTPUT FORMAT. Return ONLY the filled-in template. No preamble, no explanation,
   no markdown code fences, no commentary, no "Here is the note", no closing remarks.
   Stop as soon as the template is filled.

Template (copy this structure exactly, fill each section only with transcript content):
---
{template_text}
---

Transcript:
---
{transcript}
---

Filled note:"""


# Stop sequences guard against models that leak the next instruction header,
# echo the transcript again, or append commentary after the note. Harmless on
# well-behaved models, defensive on quirky ones (phi3, some quantized llamas).
STOP_SEQUENCES = [
    "Transcript:",
    "Template:",
    "### Instruction",
    "### Response",
    "<|user|>",
    "<|assistant|>",
    "Note:",
    "Explanation:",
]


async def run_ollama(transcript: str, template_text: str) -> str:
    if MOCK_OLLAMA:
        return _mock_response(transcript, template_text)

    prompt = PROMPT_TEMPLATE.format(
        template_text=template_text,
        transcript=transcript,
    )
    endpoint = get_ollama_endpoint()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{endpoint}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    # Low temperature keeps output close to the transcript.
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "stop": STOP_SEQUENCES,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]


def _mock_response(transcript: str, template_text: str) -> str:
    preview = transcript.strip().splitlines()
    excerpt = " ".join(preview)[:240] if preview else "(no transcript)"
    filled = template_text.replace(
        "Subjective:",
        f"Subjective:\n  Patient reports: {excerpt}",
    )
    return f"[MOCK OLLAMA — set MOCK_OLLAMA=false to use real model]\n\n{filled}"
