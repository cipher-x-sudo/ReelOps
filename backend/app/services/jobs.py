from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Niche, ReelApproval, ReelAsset, ReelJob, ReelJobStep
from .flow2api import Flow2ApiClient
from .llm import LlmClient
from .renderer import render_job

STEP_ORDER = ["topic", "script", "prompts", "asset_selection", "voiceover", "render", "export"]


def next_step(step: str) -> str:
    try:
        index = STEP_ORDER.index(step)
    except ValueError:
        return STEP_ORDER[0]
    return STEP_ORDER[min(index + 1, len(STEP_ORDER) - 1)]


def create_job(
    db: Session,
    *,
    workspace_id: str,
    user_id: str | None,
    niche_id: str,
    title: str,
    platform: str,
    language: str,
    options: dict[str, Any],
) -> ReelJob:
    niche = db.get(Niche, niche_id)
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")
    job = ReelJob(
        workspace_id=workspace_id,
        created_by_user_id=user_id,
        niche_id=niche.id,
        title=title or f"{niche.title} Reel",
        platform=platform,
        language=language,
        status="draft",
        current_step="topic",
        payload={"options": options, "niche_config": niche.config},
        artifacts={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def advance_job(db: Session, job: ReelJob, input_payload: dict[str, Any]) -> ReelJob:
    llm = LlmClient()
    flow = Flow2ApiClient()
    step = job.current_step
    job.status = "generating"
    db.commit()

    if step == "topic":
        output = await llm.generate_json(
            "Return JSON with a list of viral reel topic ideas.",
            f"Niche: {job.title}\nLanguage: {job.language}\nOptions: {input_payload}",
        )
    elif step == "script":
        topic = input_payload.get("topic") or job.payload.get("topic", {}).get("items", ["Selected topic"])[0]
        output = {
            "topic": topic,
            "script": f"Here is the hook: {topic}. Watch the story unfold scene by scene with a clear payoff at the end.",
            "word_count_target": "60-80",
        }
    elif step == "prompts":
        workflow = job.payload.get("niche_config", {}).get("workflow", {})
        video_count = int(workflow.get("video_prompt_count") or 6)
        output = {
            "image_prompts": [f"Image prompt {i}: high-retention visual for {job.title}" for i in range(1, min(video_count, 8) + 1)],
            "video_prompts": [f"Video prompt {i}: cinematic vertical scene for {job.title}" for i in range(1, video_count + 1)],
        }
    elif step == "asset_selection":
        prompts = job.payload.get("prompts", {}).get("video_prompts", [])
        assets = []
        for index, prompt in enumerate(prompts[:3], start=1):
            upstream = await flow.submit_generation(model="veo_3_1_t2v_fast_portrait", prompt=prompt)
            asset = ReelAsset(
                job_id=job.id,
                kind="video",
                label=f"Draft clip {index}",
                status="draft",
                uri=str(upstream.get("job_id") or upstream.get("mode") or "pending"),
                asset_metadata={"prompt": prompt, "upstream": upstream},
                selected=False,
            )
            db.add(asset)
            assets.append({"label": asset.label, "prompt": prompt, "upstream": upstream})
        output = {"assets": assets, "selection_mode": "manual_with_ai_suggestions"}
        job.artifacts = {**(job.artifacts or {}), "assets": assets}
    elif step == "voiceover":
        output = {
            "mode": "tts_or_upload",
            "script": job.payload.get("script", {}).get("script", ""),
            "status": "ready_for_audio",
        }
    else:
        output = {"message": f"Step {step} is handled by render/export endpoints."}

    payload = dict(job.payload or {})
    payload[step] = output
    job.payload = payload
    job.status = "awaiting_approval" if step in {"topic", "script", "prompts", "asset_selection"} else "draft"
    db.add(ReelJobStep(job_id=job.id, step_key=step, status="completed", input=input_payload, output=output))
    db.commit()
    db.refresh(job)
    return job


def approve_job_step(db: Session, job: ReelJob, *, step_key: str, user_id: str | None, decision: str, notes: str) -> ReelJob:
    db.add(ReelApproval(job_id=job.id, step_key=step_key, user_id=user_id, decision=decision, notes=notes))
    if decision == "approved" and step_key == job.current_step:
        job.current_step = next_step(job.current_step)
        job.status = "draft"
    elif decision in {"rejected", "changes_requested"}:
        job.status = "draft"
        payload = dict(job.payload or {})
        payload.setdefault("review_notes", []).append({"step": step_key, "decision": decision, "notes": notes})
        job.payload = payload
    db.commit()
    db.refresh(job)
    return job


def render_and_export_job(db: Session, job: ReelJob) -> ReelJob:
    job.status = "rendering"
    db.commit()
    exports = render_job(job)
    job.artifacts = {**(job.artifacts or {}), "exports": exports}
    job.current_step = "export"
    job.status = "completed"
    job.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job
