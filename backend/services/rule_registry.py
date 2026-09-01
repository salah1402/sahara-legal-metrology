import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("metracheck_rule_registry")

RULES_BASE_DIR = Path(__file__).resolve().parent.parent / "rules" / "packaged_commodities"


def load_registry_metadata() -> Dict[str, Any]:
    registry_file = RULES_BASE_DIR / "registry.json"
    if not registry_file.exists():
        raise FileNotFoundError(f"Registry master file not found at {registry_file}")
    with open(registry_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_rules() -> List[Dict[str, Any]]:
    meta = load_registry_metadata()
    rule_rel_paths = meta.get("rules", [])
    rules = []
    for rel_path in rule_rel_paths:
        rule_file = RULES_BASE_DIR / rel_path
        if not rule_file.exists():
            logger.warning(f"Rule file {rule_file} referenced in registry.json does not exist.")
            continue
        try:
            with open(rule_file, "r", encoding="utf-8") as f:
                rule_dict = json.load(f)
                rules.append(rule_dict)
        except Exception as e:
            logger.error(f"Failed to parse rule file {rule_file}: {e}")
    return rules


def get_active_rules(inspection_date: str) -> List[Dict[str, Any]]:
    """
    Returns only enacted rules whose effective_from <= inspection_date.
    Draft rules ('status': 'draft') are strictly excluded from evaluation.
    """
    all_rules = load_all_rules()
    active_rules = []
    # Normalize inspection date to ISO format comparison (e.g. '2026-08-31')
    insp_date_str = inspection_date.split("T")[0] if "T" in inspection_date else inspection_date

    for rule in all_rules:
        # Strictly exclude draft legislation
        if rule.get("status") != "enacted":
            continue

        effective_from = rule.get("source", {}).get("effective_from", "2011-04-01")
        if effective_from <= insp_date_str:
            active_rules.append(rule)
        else:
            logger.info(f"Rule {rule.get('rule_id')} not yet effective as of {insp_date_str} (effective: {effective_from})")

    return active_rules


def validate_rule_registry() -> Dict[str, Any]:
    """
    Validates complete integrity of the rule registry:
    - Checks required keys: rule_id, rule_number, title, source, evaluator, status.
    - Checks for duplicate rule IDs.
    - Checks for valid dates and non-empty sources.
    - Ensures draft rules are properly marked.
    """
    rules = load_all_rules()
    errors = []
    seen_ids = set()
    enacted_count = 0
    draft_count = 0

    for idx, r in enumerate(rules):
        rule_id = r.get("rule_id")
        if not rule_id:
            errors.append(f"Rule at index {idx} is missing 'rule_id'.")
            continue

        if rule_id in seen_ids:
            errors.append(f"Duplicate rule_id detected: '{rule_id}'.")
        seen_ids.add(rule_id)

        if not r.get("rule_number"):
            errors.append(f"Rule '{rule_id}' missing 'rule_number'.")
        if not r.get("title"):
            errors.append(f"Rule '{rule_id}' missing 'title'.")

        source = r.get("source", {})
        if not source or not source.get("instrument"):
            errors.append(f"Rule '{rule_id}' missing official source instrument.")
        if not source.get("effective_from"):
            errors.append(f"Rule '{rule_id}' missing source 'effective_from' date.")

        evaluator = r.get("evaluator", {})
        if not evaluator or not evaluator.get("handler"):
            errors.append(f"Rule '{rule_id}' missing evaluator handler.")

        status = r.get("status")
        if status == "enacted":
            enacted_count += 1
        elif status == "draft":
            draft_count += 1
        else:
            errors.append(f"Rule '{rule_id}' has invalid status '{status}'. Must be 'enacted' or 'draft'.")

    return {
        "valid": len(errors) == 0,
        "total_rules": len(rules),
        "enacted_rules": enacted_count,
        "draft_rules": draft_count,
        "errors": errors
    }
