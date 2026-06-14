from pathlib import Path
from typing import Any

import yaml


def load_rule(rule_path: Path) -> dict[str, Any]:
    with rule_path.open("r", encoding="utf-8") as file:
        rule = yaml.safe_load(file)

    if not isinstance(rule, dict):
        raise ValueError(f"Invalid rule file: {rule_path}")

    return rule


def load_rules_from_directory(rules_dir: Path) -> list[dict[str, Any]]:
    rule_files = sorted(rules_dir.glob("*.yaml"))

    rules: list[dict[str, Any]] = []

    for rule_file in rule_files:
        rules.append(load_rule(rule_file))

    return rules
