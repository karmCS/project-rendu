from datetime import datetime

from database import SessionLocal, Template

EPIC_FOLLOW_UP = """Visit Type: Follow Up
Date:
Provider:

Subjective:

Objective:

Assessment:

Plan:"""

EPIC_NEW_PATIENT = """Visit Type: New Patient
Date:
Provider:

Chief Complaint:

History of Present Illness:

Past Medical History:

Medications:

Allergies:

Review of Systems:

Physical Exam:

Assessment:

Plan:"""

SOAP = """Subjective:

Objective:

Assessment:

Plan:"""

DAP = """Data:

Assessment:

Plan:"""


def seed_templates() -> None:
    db = SessionLocal()
    try:
        if db.query(Template).count() > 0:
            return
        now = datetime.utcnow()
        defaults = [
            Template(
                name="Epic Follow Up",
                format_type="epic",
                template_text=EPIC_FOLLOW_UP,
                is_default=False,
                created_at=now,
                updated_at=now,
            ),
            Template(
                name="Epic New Patient",
                format_type="epic",
                template_text=EPIC_NEW_PATIENT,
                is_default=False,
                created_at=now,
                updated_at=now,
            ),
            Template(
                name="SOAP Note",
                format_type="soap",
                template_text=SOAP,
                is_default=True,
                created_at=now,
                updated_at=now,
            ),
            Template(
                name="DAP Note",
                format_type="dap",
                template_text=DAP,
                is_default=False,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(defaults)
        db.commit()
    finally:
        db.close()
