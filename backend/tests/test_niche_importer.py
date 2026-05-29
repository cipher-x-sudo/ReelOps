from pathlib import Path

from app.services.niche_importer import build_niche_config, classify_workflow, slugify


def test_slugify():
    assert slugify("PETS NICHE (CATS & DOGS) VIDEOS") == "pets-niche-cats-dogs-videos"


def test_rust_workflow_classification():
    workflow = classify_workflow("Rust Removal Videos", "Use start frame and end frame with 4 image prompts and 3 video prompts")
    assert workflow["type"] == "start_end_frame_sequence"
    assert workflow["image_prompt_count"] >= 4
    assert workflow["video_prompt_count"] >= 3


def test_build_config_has_editable_defaults():
    config = build_niche_config(Path("niches/3D HEALTH VIDEOS/3D HEALTH VIDEOS.docx"), "3D health human body 8 image prompts")
    assert config["providers"]["image_video"] == "flow2api"
    assert config["defaults"]["renderer"] if "renderer" in config["defaults"] else config["providers"]["renderer"] == "remotion"
    assert config["needs_review"] is True

