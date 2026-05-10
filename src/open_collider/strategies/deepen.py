"""Deepen strategy — new specialties in loved domain families."""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


class DeepenStrategy:
    """Generate new specialties within the same families as loved ideas."""

    def build_prompt(self, loved_ideas: list[dict], domain_history: list[dict],
                     brief: dict, config: dict) -> dict | None:
        if not loved_ideas:
            return None

        families = self._extract_families(loved_ideas, domain_history)
        if not families:
            return None

        n_domains = config.get("n_domains_per_set", 5)
        model = config.get("domain_model", "claude-opus-4-20250514")
        brief_json = json.dumps(brief, ensure_ascii=False, indent=2)

        families_text = ""
        for f in families:
            existing = ", ".join(f.get("existing_specialties", []))
            families_text += f"- **{f['name']}** (existing specialties: {existing})\n"

        prompt = f"""You are an expert in creative bisociation (Arthur Koestler). You are deepening a domain bank for an idea generation pipeline.

## Context

The following disciplinary families produced the BEST ideas in previous iterations. Generate NEW specialties within each family — different angles, different mechanisms, but same discipline.

## Families to deepen

{families_text}

## Project brief

{brief_json}

## Rules

- For EACH family, generate {n_domains} NEW specialties DIFFERENT from the existing ones
- Each specialty has an `active_principle`: 3-6 sentence narrative with counter-intuitive mechanism + open question
- Stay within the same family but explore completely different angles
- New specialties should be MORE specific and MORE surprising than existing ones

## Format — strict YAML

```yaml
sets:
  DS1:
    name: "Family name (same as above)"
    domains:
      - name: "New specific specialty"
        active_principle: >-
          A [specialist] in [specific domain] — whose work
          [focuses on / shows that / reveals that] [precise counter-intuitive mechanism].
          [Development]. [Open question toward the project's world]?
```

Generate {len(families)} sets with {n_domains} domains each.
Respond ONLY with valid YAML, nothing before or after."""

        return {"prompt": prompt, "model": model}

    def _extract_families(self, loved_ideas: list[dict],
                          domain_history: list[dict]) -> list[dict]:
        set_to_family: dict[str, dict] = {}
        for entry in domain_history:
            set_id = entry.get("set_id", "")
            name = entry.get("name", "")
            if set_id and name:
                set_to_family[set_id] = entry

        seen: set[str] = set()
        families: list[dict] = []
        for idea in loved_ideas:
            set_id = idea.get("set_id", "")
            if not set_id or set_id in seen:
                continue
            family_info = set_to_family.get(set_id)
            if family_info:
                seen.add(set_id)
                existing = [d.get("name", "") for d in family_info.get("domains", [])]
                families.append({
                    "name": family_info["name"],
                    "set_id": set_id,
                    "existing_specialties": existing,
                })
            else:
                seen.add(set_id)
                families.append({
                    "name": set_id,
                    "set_id": set_id,
                    "existing_specialties": [],
                })
        return families
