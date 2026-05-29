from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Niche
from ..rbac import Principal, require_permission
from ..schemas import NicheOut, UpdateNicheConfigRequest
from ..services.audit import record_audit
from ..services.niche_importer import import_niches

router = APIRouter(prefix="/api/reels/niches", tags=["niches"])


@router.get("", response_model=list[NicheOut])
def list_niches(
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> list[NicheOut]:
    rows = db.query(Niche).order_by(Niche.title).all()
    return [NicheOut.model_validate(row) for row in rows]


@router.post("/import", response_model=list[NicheOut])
def import_all_niches(
    principal: Principal = Depends(require_permission("niches.manage")),
    db: Session = Depends(get_db),
) -> list[NicheOut]:
    rows = import_niches(db)
    record_audit(db, principal=principal, action="niches.import", details={"count": len(rows)})
    db.commit()
    return [NicheOut.model_validate(row) for row in db.query(Niche).order_by(Niche.title).all()]


@router.get("/{niche_id}", response_model=NicheOut)
def get_niche(
    niche_id: str,
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> NicheOut:
    row = db.get(Niche, niche_id)
    if not row:
        raise HTTPException(status_code=404, detail="Niche not found")
    return NicheOut.model_validate(row)


@router.patch("/{niche_id}", response_model=NicheOut)
def update_niche(
    niche_id: str,
    payload: UpdateNicheConfigRequest,
    principal: Principal = Depends(require_permission("niches.manage")),
    db: Session = Depends(get_db),
) -> NicheOut:
    row = db.get(Niche, niche_id)
    if not row:
        raise HTTPException(status_code=404, detail="Niche not found")
    row.config = payload.config
    row.needs_review = payload.needs_review
    record_audit(db, principal=principal, action="niches.update", target_type="niche", target_id=row.id)
    db.commit()
    db.refresh(row)
    return NicheOut.model_validate(row)

