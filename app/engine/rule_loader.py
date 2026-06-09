from pathlib import Path
from typing import Any

import yaml


def load_rule(rule_path: str | Path) -> dict[str, Any]:
    path = Path(rule_path)

    if not path.exists():
        raise FileNotFoundError(f"Rule file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        rule = yaml.safe_load(file)

    if not isinstance(rule, dict):
        raise ValueError(f"Rule file must contain a YAML object: {path}")

    return rule
