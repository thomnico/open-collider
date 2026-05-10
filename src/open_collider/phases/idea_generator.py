"""Idea generation — prompt assembly and response parsing. No LLM calls."""

from __future__ import annotations

import logging
import random
import re

from open_collider.prompt_resolver import PromptResolver
from open_collider.scoring.data_loader import DataLoader

logger = logging.getLogger(__name__)


def sample_combos(
    text_ids: list[str],
    set_ids: list[str],
    n_combos: int,
    stratified: bool = True,
) -> list[tuple[str, str]]:
    """Draw n_combos (text_id, set_id) pairs.

    If stratified: guarantees at least 1 combo per set for coverage.
    """
    if not stratified:
        return [
            (random.choice(text_ids), random.choice(set_ids))
            for _ in range(n_combos)
        ]

    combos: list[tuple[str, str]] = []
    if n_combos >= len(set_ids):
        shuffled = list(set_ids)
        random.shuffle(shuffled)
        for s_id in shuffled:
            combos.append((random.choice(text_ids), s_id))
        remaining = n_combos - len(set_ids)
        for _ in range(remaining):
            combos.append((random.choice(text_ids), random.choice(set_ids)))
    else:
        sampled = random.sample(set_ids, n_combos)
        for s_id in sampled:
            combos.append((random.choice(text_ids), s_id))

    return combos


class IdeaGenerator:
    """Assemble idea generation prompts and parse responses."""

    def __init__(self, config: dict, prompt_resolver: PromptResolver) -> None:
        self.config = config
        self.prompt_resolver = prompt_resolver

    def assemble_prompt(
        self,
        text_id: str,
        set_id: str,
        data_loader: DataLoader,
    ) -> str:
        """Build the full generation prompt for one combo."""
        template_path = self.prompt_resolver.resolve("idea_generation.md")
        template = template_path.read_text(encoding="utf-8")

        meta, content = data_loader.load_text_input(text_id)
        domain_set = data_loader.load_domain_set(set_id)
        domain_list = data_loader.format_domain_list(domain_set)
        forbidden = data_loader.format_forbidden_topics(meta)
        brief_content = self.prompt_resolver.load_brief_content()

        prompt = template
        prompt = prompt.replace("{brief_content}", brief_content)
        prompt = prompt.replace("{text_input}", content)
        prompt = prompt.replace("{domain_list}", domain_list)
        prompt = prompt.replace("{forbidden_topics}", forbidden)

        output_format = self.config.get("output_format", "")
        if output_format and "{output_format}" not in prompt:
            prompt += f"\n\n---\nEXPECTED OUTPUT FORMAT: {output_format.strip()}"

        return prompt

    def parse_response(self, content: str, combo: str) -> list[dict]:
        """Parse LLM response into structured idea dicts.

        combo format: {text_id}_{strategy}_{set_id}
        """
        parts = combo.split("_")
        text_id = parts[0] if parts else combo
        set_id = parts[-1] if len(parts) >= 3 else (parts[1] if len(parts) > 1 else "")

        ideas: list[dict] = []

        # Strategy: split on idea headers first, then extract number + text.
        # Header prefix matches "Idea" / "Idée" / "Idee" (bilingual EN/FR/NL) or "Concept", optional.
        split_content = "\n" + content
        sections = re.split(r'\n#{1,3}\s*(?:[Ii]d(?:ea|ée|ee)\s+|[Cc]oncept\s+)?(\d+)[.:\s\-]*', split_content)
        if len(sections) >= 3:
            matches = [(sections[i], sections[i + 1]) for i in range(1, len(sections), 2)]
        else:
            matches = []

        if not matches:
            numbered = r"(?:^|\n)\s*(\d+)\.\s+(.*?)(?=\n\s*\d+\.\s+|\Z)"
            matches = re.findall(numbered, content, re.DOTALL)

        if not matches:
            bold = r"(?:^|\n)\*\*(?:[Ii]d(?:ea|ée|ee)\s+)?(\d+)\.?\*\*\s*(.*?)(?=\n\*\*(?:[Ii]d(?:ea|ée|ee)\s+)?\d+|\Z)"
            matches = re.findall(bold, content, re.DOTALL)

        for num_str, text in matches:
            text_clean = text.strip()
            if text_clean:
                ideas.append({
                    "combo": combo,
                    "idea_num": int(num_str),
                    "text": text_clean,
                    "text_id": text_id,
                    "set_id": set_id,
                })

        if not ideas:
            logger.warning("Combo %s — no ideas parsed", combo)

        return ideas
