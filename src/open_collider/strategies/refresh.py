"""Refresh strategy — mechanism-derived domains from loved+liked ideas."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


class RefreshStrategy:
    """Extract causal mechanisms from best ideas, find new disciplines with same patterns."""

    def build_prompt(self, loved_ideas: list[dict], liked_ideas: list[dict],
                     brief: dict, config: dict) -> dict | None:
        all_ideas = loved_ideas + liked_ideas
        if not all_ideas:
            return None

        n_sets = config.get("n_sets", 12)
        n_domains = config.get("n_domains_per_set", 5)
        model = config.get("domain_model", "claude-opus-4-20250514")
        brief_json = json.dumps(brief, ensure_ascii=False, indent=2)

        ideas_text = "\n\n".join(
            f"**Idea {i+1}** (score {idea.get('score_aggregate', idea.get('score', '?'))}):\n"
            f"{idea.get('text', '')}"
            for i, idea in enumerate(all_ideas[:15])
        )

        prompt = f"""You are an expert in creative bisociation (Arthur Koestler). You are refreshing a domain bank based on its best previous results.

## Context — Best ideas from previous iterations

{ideas_text}

## Project brief

{brief_json}

## Your mission

1. Identify the CAUSAL MECHANISMS that made these ideas work. Not topics — structural patterns.
2. For each mechanism, generate a domain set with {n_domains} specialists from COMPLETELY DIFFERENT disciplines that exhibit the SAME structural pattern.
3. New domains must be from disciplines NOT already present in the ideas above.

## Rules

- Generate {n_sets} sets, each organized around a different causal mechanism
- Each domain has an `active_principle`: 3-6 sentence narrative with counter-intuitive mechanism + open question
- Maximize disciplinary distance from the source ideas
- The mechanism must TRANSFER structurally, not just be a surface analogy

## Format — strict YAML

```yaml
sets:
  DS1:
    name: "Mechanism: [name of the causal pattern]"
    domains:
      - name: "Specific specialty from a distant discipline"
        active_principle: >-
          A [specialist] — whose work [reveals the same structural pattern].
          [Development]. [Open question toward the project's world]?
```

Generate {n_sets} sets with {n_domains} domains each.
Respond ONLY with valid YAML, nothing before or after."""

        return {"prompt": prompt, "model": model}
