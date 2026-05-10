"""Fresh domain generation — random distant domains, excluding history."""

from __future__ import annotations

import json
import logging
import re

import yaml

logger = logging.getLogger(__name__)


def parse_domain_response(response: str) -> str:
    """Extract and validate YAML domain bank from LLM response.

    Raises ValueError if YAML is invalid or missing 'sets' key.
    """
    match = re.search(r"```ya?ml\s*\n(.*?)```", response, re.DOTALL)
    yaml_content = match.group(1) if match else response
    try:
        bank = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Domain response is not valid YAML: {e}")
    if not isinstance(bank, dict) or "sets" not in bank:
        raise ValueError(f"Domain response missing 'sets' key. Got: {type(bank)}")
    if not bank["sets"]:
        raise ValueError("Domain response has empty 'sets' — no domains generated")
    return yaml_content


class FreshStrategy:
    """Generate random domains deduped from all previous iterations."""

    def build_prompt(self, domain_history: list[dict], brief: dict,
                     config: dict) -> dict:
        n_sets = config.get("n_sets", 12)
        n_domains = config.get("n_domains_per_set", 5)
        model = config.get("domain_model", "claude-opus-4-20250514")
        brief_json = json.dumps(brief, ensure_ascii=False, indent=2)

        exclusion_text = ""
        if domain_history:
            families = [d.get("name", "") for d in domain_history if d.get("name")]
            if families:
                exclusion_text = (
                    "\n\n## EXCLUDED FAMILIES (already used — DO NOT reuse)\n\n"
                    + "\n".join(f"- {f}" for f in families)
                    + "\n\nGenerate domain sets from COMPLETELY DIFFERENT disciplinary families."
                )

        prompt = f"""You are an expert in creative bisociation (Arthur Koestler). Generate a bank of structurally distant knowledge domains for an idea generation pipeline.

## Project brief

{brief_json}

## Rules

- Each domain set represents a DIFFERENT disciplinary family
- Each domain has an `active_principle`: a 3-6 sentence narrative describing a counter-intuitive mechanism and ending with an open question bridging to the project's world
- Maximize distance from the project's territory
- Maximize diversity BETWEEN sets
{exclusion_text}

## Format — strict YAML

```yaml
sets:
  DS1:
    name: "Disciplinary family name"
    domains:
      - name: "Specific specialty"
        active_principle: >-
          A [specialist] in [specific domain] — whose work
          [focuses on / shows that / reveals that] [precise counter-intuitive mechanism].
          [Development]. [Open question toward the project's world]?
```

Generate {n_sets} sets with {n_domains} domains each.
Respond ONLY with valid YAML, nothing before or after."""

        return {"prompt": prompt, "model": model}
