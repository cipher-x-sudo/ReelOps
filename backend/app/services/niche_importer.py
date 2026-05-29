from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from docx import Document
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Niche

try:
    import fitz
except Exception:  # pragma: no cover - import availability is environment-specific
    fitz = None


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "niche"


def _extract_docx(path: Path) -> str:
    document = Document(str(path))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _extract_pdf(path: Path) -> str:
    if fitz is None:
        return ""
    doc = fitz.open(path)
    pages = [page.get_text("text") for page in doc[: min(20, len(doc))]]
    return "\n".join(pages)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pdf":
        return _extract_pdf(path)
    return path.read_text(encoding="utf-8", errors="ignore")


def _number_from_text(pattern: str, text: str, fallback: int) -> int:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return fallback
    try:
        return int(match.group(1))
    except Exception:
        return fallback


def classify_workflow(title: str, text: str) -> dict[str, Any]:
    haystack = f"{title}\n{text}".lower()
    image_count = _number_from_text(r"(\d+)\s+image prompts?", haystack, 6)
    video_count = _number_from_text(r"(\d+)\s+video prompts?", haystack, 6)

    if "rust removal" in haystack or "start frame" in haystack and "end frame" in haystack:
        workflow_type = "start_end_frame_sequence"
        image_count = max(image_count, 4)
        video_count = max(video_count, 3)
    elif "street interview" in haystack:
        workflow_type = "interactive_interview"
        image_count = max(image_count, 3)
        video_count = max(video_count, 3)
    elif "sora" in haystack or "single continuous shot" in haystack:
        workflow_type = "single_prompt_video"
        image_count = 0
        video_count = 1
    elif "3d health" in haystack or "human body" in haystack:
        workflow_type = "scripted_scene_pack"
        image_count = max(image_count, 8)
        video_count = max(video_count, 8)
    else:
        workflow_type = "guided_scene_pack"

    return {
        "type": workflow_type,
        "steps": [
            "topic",
            "script",
            "prompts",
            "asset_selection",
            "voiceover",
            "render",
            "export",
        ],
        "image_prompt_count": image_count,
        "video_prompt_count": video_count,
        "approval_points": ["topic", "script", "prompts", "asset_selection", "render"],
    }


def build_niche_config(path: Path, text: str) -> dict[str, Any]:
    title = path.stem.replace(" MASTER PROMPT", "").strip()
    workflow = classify_workflow(title, text)
    excerpt = text[:6000]
    return {
        "schema_version": 1,
        "title": title,
        "slug": slugify(title),
        "source_file": str(path),
        "defaults": {
            "language": "English",
            "platforms": ["facebook", "instagram", "tiktok", "youtube_shorts"],
            "duration_policy": "per_niche",
            "render_template": workflow["type"],
            "caption_output": ["burned_in", "srt", "vtt"],
            "asset_selection": "manual_with_ai_suggestions",
            "quality_mode": "draft_then_final",
        },
        "workflow": workflow,
        "providers": {
            "prompt": "configured",
            "image_video": "flow2api",
            "tts": "configured_or_upload",
            "renderer": "remotion",
        },
        "preserved_instructions_excerpt": excerpt,
        "needs_review": True,
    }


def import_niches(db: Session) -> list[Niche]:
    settings.niche_configs_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Niche] = []
    files = sorted(
        p for p in settings.niches_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".docx", ".pdf", ".txt"}
    )
    for path in files:
        text = extract_text(path)
        config = build_niche_config(path, text)
        slug = config["slug"]
        target = settings.niche_configs_dir / f"{slug}.json"
        target.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

        niche = db.query(Niche).filter(Niche.slug == slug).first()
        if niche:
            niche.title = config["title"]
            niche.source_path = str(path)
            niche.source_type = path.suffix.lower().lstrip(".")
            niche.config = config
            niche.needs_review = bool(config["needs_review"])
        else:
            niche = Niche(
                slug=slug,
                title=config["title"],
                source_path=str(path),
                source_type=path.suffix.lower().lstrip("."),
                config=config,
                needs_review=True,
            )
            db.add(niche)
        imported.append(niche)
    db.commit()
    return imported

