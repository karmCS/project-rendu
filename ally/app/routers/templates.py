from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Template, get_db
from models import TemplateCreate, TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


def _unset_other_defaults(db: Session, except_id: Optional[int] = None) -> None:
    query = db.query(Template).filter(Template.is_default.is_(True))
    if except_id is not None:
        query = query.filter(Template.id != except_id)
    for tpl in query.all():
        tpl.is_default = False


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.query(Template).order_by(Template.id).all()


@router.post("", response_model=TemplateOut)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)):
    if body.is_default:
        _unset_other_defaults(db)
    now = datetime.utcnow()
    tpl = Template(
        name=body.name,
        format_type=body.format_type,
        template_text=body.template_text,
        is_default=body.is_default,
        created_at=now,
        updated_at=now,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    body: TemplateCreate,
    db: Session = Depends(get_db),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.is_default:
        _unset_other_defaults(db, except_id=template_id)
    tpl.name = body.name
    tpl.format_type = body.format_type
    tpl.template_text = body.template_text
    tpl.is_default = body.is_default
    tpl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    if db.query(Template).count() <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the last remaining template",
        )
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tpl)
    db.commit()
    return {"deleted": True}
