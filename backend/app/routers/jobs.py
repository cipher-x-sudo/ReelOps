from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReelJob
from ..rbac import Principal, require_permission
from ..schemas import AdvanceJobRequest, ApprovalRequest, CreateJobRequest, JobOut
from ..services.audit import record_audit
from ..services.jobs import advance_job, approve_job_step, create_job, render_and_export_job

router = APIRouter(prefix="/api/reels/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> list[JobOut]:
    rows = (
        db.query(ReelJob)
        .filter(ReelJob.workspace_id == principal.workspace_id)
        .order_by(ReelJob.created_at.desc())
        .limit(100)
        .all()
    )
    return [JobOut.model_validate(row) for row in rows]


@router.post("", response_model=JobOut)
def create_reel_job(
    payload: CreateJobRequest,
    principal: Principal = Depends(require_permission("jobs.create")),
    db: Session = Depends(get_db),
) -> JobOut:
    job = create_job(
        db,
        workspace_id=principal.workspace_id,
        user_id=principal.actor_user_id,
        niche_id=payload.niche_id,
        title=payload.title,
        platform=payload.platform,
        language=payload.language,
        options=payload.options,
    )
    record_audit(db, principal=principal, action="jobs.create", target_type="job", target_id=job.id)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    principal: Principal = Depends(require_permission("jobs.view")),
    db: Session = Depends(get_db),
) -> JobOut:
    job = db.get(ReelJob, job_id)
    if not job or job.workspace_id != principal.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@router.post("/{job_id}/advance", response_model=JobOut)
async def advance_reel_job(
    job_id: str,
    payload: AdvanceJobRequest,
    principal: Principal = Depends(require_permission("jobs.create")),
    db: Session = Depends(get_db),
) -> JobOut:
    job = db.get(ReelJob, job_id)
    if not job or job.workspace_id != principal.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    job = await advance_job(db, job, payload.input)
    record_audit(db, principal=principal, action="jobs.advance", target_type="job", target_id=job.id, details={"step": job.current_step})
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.post("/{job_id}/approve", response_model=JobOut)
def approve_reel_job(
    job_id: str,
    payload: ApprovalRequest,
    principal: Principal = Depends(require_permission("jobs.approve")),
    db: Session = Depends(get_db),
) -> JobOut:
    job = db.get(ReelJob, job_id)
    if not job or job.workspace_id != principal.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    job = approve_job_step(
        db,
        job,
        step_key=payload.step_key,
        user_id=principal.actor_user_id,
        decision=payload.decision,
        notes=payload.notes,
    )
    record_audit(
        db,
        principal=principal,
        action="jobs.approve",
        target_type="job",
        target_id=job.id,
        details={"step": payload.step_key, "decision": payload.decision},
    )
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.post("/{job_id}/render", response_model=JobOut)
def render_reel_job(
    job_id: str,
    principal: Principal = Depends(require_permission("jobs.render")),
    db: Session = Depends(get_db),
) -> JobOut:
    job = db.get(ReelJob, job_id)
    if not job or job.workspace_id != principal.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    job = render_and_export_job(db, job)
    record_audit(db, principal=principal, action="jobs.render", target_type="job", target_id=job.id)
    db.commit()
    db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/{job_id}/artifacts")
def get_job_artifacts(
    job_id: str,
    principal: Principal = Depends(require_permission("exports.download")),
    db: Session = Depends(get_db),
):
    job = db.get(ReelJob, job_id)
    if not job or job.workspace_id != principal.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "artifacts": job.artifacts}

