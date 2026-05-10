"""Idea scoring — prompt assembly and response parsing. No LLM calls.

Uses a judge.md template with hardcoded 5-axis scoring layout.
"""

from __future__ import annotations

import logging
import re

from open_collider.prompt_resolver import PromptResolver
from open_collider.scoring.score_parser import parse_scoring_table, extract_judge_notes

logger = logging.getLogger(__name__)

# Default weights — can be overridden per project via judge_axes in project_config.yaml
DEFAULT_WEIGHTS = {
    "originality": 0.25,
    "resistance": 0.20,
    "thesis_density": 0.20,
    "concrete_grounding": 0.20,
    "cognitive_load": 0.15,
}

DEFAULT_THRESHOLD = 4.2
DRIFT_THRESHOLD = 4.0
MIN_IDEAS_BEFORE_DRIFT = 3
DRIFT_STEP = 0.1
BATCH_SIZE = 25


class IdeaScorer:
    """Assemble scoring prompts and parse responses."""

    def __init__(self, config: dict, prompt_resolver: PromptResolver | None = None) -> None:
        self.config = config
        self.prompt_resolver = prompt_resolver
        # Axes are fixed (5 hardcoded names). Weights are configurable per project.
        self.weights = config.get("judge_axes", DEFAULT_WEIGHTS)

    def assemble_prompt(
        self,
        ideas: list[dict],
        ref_high: list[dict] | None = None,
        ref_low: list[dict] | None = None,
    ) -> str:
        """Build the judge prompt from judge.md template + calibration refs."""
        prompt_path = self.prompt_resolver.resolve("judge.md")
        template = prompt_path.read_text(encoding="utf-8")

        # Replace calibration section with dynamic refs if provided
        if ref_high or ref_low:
            ref_high_text = self._format_references(ref_high or [], "high")
            ref_low_text = self._format_references(ref_low or [], "low")

            new_calibration = (
                "## CALIBRATION FRAMEWORK\n\n"
                "These excerpts come from real project content. "
                "They define what a structurally strong idea looks like in this specific context.\n\n"
                "### High-value reference ideas (expected score >= 4.0)\n\n"
                f"{ref_high_text}\n\n"
                "### Low-value reference ideas (expected score < 3.5)\n\n"
                f"{ref_low_text}"
            )

            calibration_pattern = re.compile(
                r"## CALIBRATION FRAMEWORK.*?(?=## IDEAS TO EVALUATE)",
                re.DOTALL,
            )
            template = calibration_pattern.sub(new_calibration + "\n\n---\n\n", template)

        ideas_text = self.format_ideas_for_prompt(ideas)
        return template.replace("{ideas}", ideas_text)

    def parse_response(self, response: str, ideas: list[dict]) -> list[dict]:
        """Parse scoring response into scored idea dicts.

        Recalculates score_aggregate from per-axis scores using hardcoded weights.
        Does NOT set 'retained' — use apply_threshold() for that.
        """
        axis_scores = parse_scoring_table(response)
        judge_notes = extract_judge_notes(response)

        scored = []
        num_to_idea = {i.get("_global_num", i["idea_num"]): i for i in ideas}

        for ax in axis_scores:
            idea = num_to_idea.get(ax.idea_num)
            if not idea:
                continue

            scores = {
                "originality": ax.originality,
                "resistance": ax.resistance,
                "thesis_density": ax.thesis_density,
                "concrete_grounding": ax.concrete_grounding,
                "cognitive_load": ax.cognitive_load,
            }

            # Recalculate aggregate from project weights
            score_aggregate = round(
                sum(scores[k] * self.weights[k] for k in scores), 2
            )

            result = {k: v for k, v in idea.items() if not k.startswith("_")}
            result["idea_num"] = idea.get("_orig_idea_num", idea["idea_num"])
            result["scores"] = scores
            result["score_aggregate"] = score_aggregate
            result["judge_note"] = judge_notes.get(ax.idea_num, "")
            scored.append(result)

        return scored

    @staticmethod
    def _format_references(refs: list[dict], level: str) -> str:
        """Format calibration references. Accepts both EN and FR field names."""
        lines = []
        for i, ref in enumerate(refs, 1):
            text = ref.get("text", ref.get("extrait", ""))
            why = ref.get("why", ref.get("pourquoi", ""))
            lines.append(f"**Ref-{i}**\n> {text}\n*Why {level}: {why}*")
        return "\n\n".join(lines)

    @staticmethod
    def format_ideas_for_prompt(ideas: list[dict]) -> str:
        lines = []
        for idea in ideas:
            num = idea.get("_global_num", idea["idea_num"])
            lines.append(f"{num}. {idea['text']}")
        return "\n\n".join(lines)


def apply_threshold(scored_ideas: list[dict], config: dict) -> list[dict]:
    """Set 'retained' field based on score_aggregate vs threshold.

    Drift: if fewer than min_ideas pass, step down until enough pass or floor reached.
    """
    threshold = config.get("score_threshold", DEFAULT_THRESHOLD)
    drift_floor = config.get("drift_threshold", DRIFT_THRESHOLD)
    min_ideas = config.get("min_ideas_before_drift", MIN_IDEAS_BEFORE_DRIFT)
    step = config.get("drift_step", DRIFT_STEP)

    current_threshold = threshold
    while current_threshold > drift_floor:
        passing = [i for i in scored_ideas if i.get("score_aggregate", 0) >= current_threshold]
        if len(passing) >= min_ideas:
            break
        current_threshold = round(current_threshold - step, 2)
    current_threshold = max(current_threshold, drift_floor)

    for idea in scored_ideas:
        score = idea.get("score_aggregate", 0)
        idea["retained"] = score >= current_threshold
        idea["threshold_used"] = current_threshold

    return scored_ideas
