"""Configuration loading and merging."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_config() -> dict:
    """Load default config from data/config.yaml."""
    config_path = Path(__file__).parent / "data" / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("generic_pipeline", {})


def load_project_config(project_dir: str) -> dict:
    """Load defaults + project overrides.

    Merge rules:
    - project_config.yaml values override defaults (shallow merge)
    - output_format in project_config.yaml wins over brief
    """
    config = load_config()
    project_path = Path(project_dir)
    project_cfg_path = project_path / "project_config.yaml"
    if project_cfg_path.is_file():
        with open(project_cfg_path, encoding="utf-8") as f:
            project_cfg = yaml.safe_load(f) or {}
        for key, value in project_cfg.items():
            config[key] = value  # shallow override
    return config
