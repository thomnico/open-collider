"""Resolve prompt templates per project."""

from __future__ import annotations

import json
from pathlib import Path


class PromptResolver:
    """Find and load prompt templates for a project."""

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir

    def resolve(self, prompt_filename: str) -> Path:
        """Find a prompt file in the project's prompts/ directory."""
        path = self._project_dir / "prompts" / prompt_filename
        if not path.is_file():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path

    def load_brief_content(self) -> str:
        """Load brief_validated.json and format for prompt injection."""
        brief_path = self._project_dir / "brief_validated.json"
        if not brief_path.is_file():
            return ""
        with open(brief_path, encoding="utf-8") as f:
            brief = json.load(f)
        return _format_brief_for_prompt(brief)


def _format_brief_for_prompt(brief: dict) -> str:
    """Format a brief dict as readable text for prompt injection."""
    lines = []
    for key, value in brief.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"**{label}:**")
            for item in value:
                if isinstance(item, dict):
                    parts = [f"{k}: {v}" for k, v in item.items()]
                    lines.append(f"  - {', '.join(parts)}")
                else:
                    lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"**{label}:**")
            for k, v in value.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"**{label}:** {value}")
    return "\n".join(lines)
