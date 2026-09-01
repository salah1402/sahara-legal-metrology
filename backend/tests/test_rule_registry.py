"""
Phase 3 Rule Registry Integrity & Schema Validation Test Suite
Tests:
- Master registry loads cleanly
- Rule JSON files exist and conform to schema
- No duplicate rule IDs
- Mandatory legal sources and Gazette notifications present
- Valid effective_from ISO dates
- Draft rules marked with status="draft" and excluded from active evaluation
"""

import unittest
from backend.services.rule_registry import (
    load_registry_metadata,
    load_all_rules,
    get_active_rules,
    validate_rule_registry
)


class TestRuleRegistryValidation(unittest.TestCase):

    def test_01_registry_master_metadata(self):
        """Test master registry.json loads with required framework info."""
        meta = load_registry_metadata()
        self.assertEqual(meta.get("registry_version"), "PCR-2011-CURRENT")
        self.assertIn("Legal Metrology", meta.get("framework", ""))
        self.assertGreater(len(meta.get("official_sources", [])), 3)
        self.assertGreater(len(meta.get("rules", [])), 10)

    def test_02_rule_registry_validator(self):
        """Test automated validation checks for all rules."""
        res = validate_rule_registry()
        self.assertTrue(res["valid"], f"Registry validation failed with errors: {res.get('errors')}")
        self.assertGreater(res["enacted_rules"], 15)
        self.assertGreaterEqual(res["draft_rules"], 1)
        self.assertEqual(len(res["errors"]), 0)

    def test_03_draft_rule_exclusion(self):
        """Test that draft rules with status='draft' are strictly excluded from active evaluation."""
        active_rules = get_active_rules("2026-08-31")
        for r in active_rules:
            self.assertEqual(r.get("status"), "enacted")
            self.assertNotEqual(r.get("status"), "draft")
            self.assertNotEqual(r.get("rule_id"), "PCR-2025-DRAFT-AMEND-2")

    def test_04_effective_date_timeline(self):
        """Test that historical inspection dates do not activate future amendments."""
        # As of 2015 (before 2017/2021/2023 amendments):
        rules_2015 = get_active_rules("2015-01-01")
        rule_ids_2015 = [r["rule_id"] for r in rules_2015]

        # Unit sale price was enacted in 2021/2022 (GSR 784(E))
        self.assertNotIn("PCR-2011-R6-1-m", rule_ids_2015)
        # Electronic QR was enacted in 2023 (GSR 512(E))
        self.assertNotIn("PCR-2011-R-ELEC-QR", rule_ids_2015)

        # As of 2026, all current amendments are active:
        rules_2026 = get_active_rules("2026-08-31")
        rule_ids_2026 = [r["rule_id"] for r in rules_2026]
        self.assertIn("PCR-2011-R6-1-m", rule_ids_2026)
        self.assertIn("PCR-2011-R-ELEC-QR", rule_ids_2026)


if __name__ == "__main__":
    unittest.main()
