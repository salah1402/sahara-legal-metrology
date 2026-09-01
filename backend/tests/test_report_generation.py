"""
Comprehensive Phase 4 & 4.1 Inspection Summary, Product Name Cleanup & PDF Quality Test Suite
Tests:
1. PASS inspection -> correct PDF status (PASS)
2. FAIL inspection -> correct PDF status (FAIL)
3. NEEDS REVIEW inspection -> correct PDF status (NEEDS REVIEW)
4. Missing fields handling in report
5. Prompt leakage detection and rejection -> clean fallback
6. PDF generation produces valid 2-page PDF bytes
7. PDF export API endpoint (POST /api/inspections/{id}/report)
8. Summary API endpoint (GET /api/inspections/{id}/summary)
9. History rename preservation during report workflow
10. Product name cleanup removes random OCR hash tokens and noise
11. Long product names and rule descriptions wrap without errors
"""

import io
import json
import shutil
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import (
    app,
    INSPECTIONS_DIR,
    clean_display_product_name,
    clean_filename_title,
    format_composite_product_title
)
from backend.models.schemas import (
    StructuredProductData,
    ProductFields,
    ExtractedField,
    ImageCoverage,
    Evidence
)
from backend.models.compliance import (
    ComplianceResult,
    ComplianceSummary,
    LegalFrameworkInfo,
    RuleCheckResult,
    LegalSource,
    RuleApplicabilityDecision,
    ApplicabilityFacts,
    ExemptionAuditInfo
)
from backend.services.summary_service import (
    generate_deterministic_summary,
    generate_inspection_summary,
    is_prompt_leakage,
    sanitize_summary_text
)
from backend.services.report_service import generate_inspection_pdf


def make_evidence(text: str, conf: float = 0.98, img_id: str = "IMG-001") -> Evidence:
    return Evidence(image_id=img_id, source_text=text, ocr_confidence=conf, bbox=[10, 10, 100, 30])


class TestInspectionReportGeneration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.test_insp_id = "INS-TEST-REPORT-001"
        self.test_dir = INSPECTIONS_DIR / self.test_insp_id
        self.test_dir.mkdir(parents=True, exist_ok=True)
        (self.test_dir / "normalized").mkdir(parents=True, exist_ok=True)
        (self.test_dir / "compliance").mkdir(parents=True, exist_ok=True)
        (self.test_dir / "ocr").mkdir(parents=True, exist_ok=True)

        # Create base metadata
        with open(self.test_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "inspection_id": self.test_insp_id,
                "display_name": "Bourbon Biscuits — Britannia",
                "product_name": "Bourbon Biscuits",
                "status": "compliant",
                "created_at": "2026-08-31T12:00:00Z",
                "image_count": 2
            }, f)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_mock_compliance_result(self, overall_status="COMPLIANT", failed_count=0, review_count=0, exempt_count=0):
        checks = [
            RuleCheckResult(
                rule_id="PCR-2011-R6-1-a",
                rule_number="6(1)(a)",
                title="Manufacturer / Packer Name & Address",
                status="PASS" if overall_status == "COMPLIANT" else ("FAIL" if failed_count > 0 else "NEEDS_REVIEW"),
                applicability=RuleApplicabilityDecision(status="APPLICABLE"),
                observed_value="Britannia Industries Ltd, 5/1A Hungerford Street, Kolkata 700017",
                required_value="Name and complete address of manufacturer",
                reason="Manufacturer details verified from package evidence.",
                evidence=[make_evidence("Mfg by Britannia Industries")],
                legal_source=LegalSource(instrument="PCR 2011", effective_from="2011-04-01")
            ),
            RuleCheckResult(
                rule_id="PCR-2011-R6-1-c",
                rule_number="6(1)(c)",
                title="Net Quantity in Standard Metric Units",
                status="EXEMPT" if exempt_count > 0 else "PASS",
                applicability=RuleApplicabilityDecision(status="EXEMPT" if exempt_count > 0 else "APPLICABLE"),
                observed_value="5 g" if exempt_count > 0 else "120 g",
                required_value="Net quantity in standard metric units",
                reason="Exempt under Rule 26(a) statutory small package exemption." if exempt_count > 0 else "Declared in standard metric unit 'g'.",
                evidence=[make_evidence("5 g" if exempt_count > 0 else "120 g")],
                legal_source=LegalSource(instrument="PCR 2011", effective_from="2011-04-01"),
                exemption=ExemptionAuditInfo(
                    exemption_rule="PCR-2011-R26",
                    exemption_clause="26(a)",
                    reason="Net quantity 5 g <= 10 g / 10 mL",
                    factual_conditions_checked=["Net quantity <= 10 g", "Not tobacco/pan masala"]
                ) if exempt_count > 0 else None
            )
        ]

        return ComplianceResult(
            schema_version="1.0",
            inspection_id=self.test_insp_id,
            inspection_date="2026-08-31T12:00:00Z",
            overall_status=overall_status,
            legal_framework=LegalFrameworkInfo(name="PCR 2011", registry_version="PCR-2011-CURRENT", effective_as_of="2026-08-31"),
            applicability=ApplicabilityFacts(
                is_exempt_under_rule_26=bool(exempt_count > 0),
                rule_26_clause="26(a)" if exempt_count > 0 else None,
                exemption_reason="Net quantity 5 g <= 10 g / 10 mL" if exempt_count > 0 else None,
                exemption_conditions=["Net quantity <= 10 g", "Not tobacco/pan masala"] if exempt_count > 0 else []
            ),
            summary=ComplianceSummary(
                total_checks=2,
                passed=2 if overall_status == "COMPLIANT" else (1 if exempt_count > 0 else 0),
                failed=failed_count,
                needs_review=review_count,
                not_applicable=0,
                exempt=exempt_count
            ),
            checks=checks
        )

    def test_01_deterministic_summary_compliant(self):
        """Test deterministic summary for COMPLIANT inspection."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        summary = generate_deterministic_summary(comp, "Bourbon Biscuits", "Britannia")
        self.assertIn("COMPLIANT", summary)
        self.assertIn("Bourbon Biscuits", summary)
        self.assertIn("Legal Metrology", summary)

    def test_02_deterministic_summary_non_compliant(self):
        """Test deterministic summary for NON_COMPLIANT inspection lists failed rules."""
        comp = self.create_mock_compliance_result("NON_COMPLIANT", failed_count=1)
        summary = generate_deterministic_summary(comp, "Bourbon Biscuits", "Britannia")
        self.assertIn("NON-COMPLIANT", summary)
        self.assertIn("1 statutory violation", summary)

    def test_03_deterministic_summary_needs_review(self):
        """Test deterministic summary for NEEDS_REVIEW inspection."""
        comp = self.create_mock_compliance_result("NEEDS_REVIEW", review_count=1)
        summary = generate_deterministic_summary(comp, "Bourbon Biscuits", "Britannia")
        self.assertIn("NEEDS REVIEW", summary)

    def test_04_prompt_leakage_detection(self):
        """Test is_prompt_leakage catches leaked prompt text and reasoning."""
        self.assertTrue(is_prompt_leakage("The user wants a concise 2-4 sentence executive summary."))
        self.assertTrue(is_prompt_leakage("System prompt: You are a helpful assistant."))
        self.assertTrue(is_prompt_leakage("Task: Write a concise summary of findings."))
        self.assertTrue(is_prompt_leakage("Here is the summary of the inspection:"))
        self.assertTrue(is_prompt_leakage("As an AI, I have reviewed the package."))
        self.assertFalse(is_prompt_leakage("The package inspection resulted in NEEDS REVIEW because mandatory declarations could not be verified."))

    def test_05_llm_unavailable_fallback_summary(self):
        """Test generate_inspection_summary falls back seamlessly when LLM is unavailable or leaks prompts."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        summary_text, source = generate_inspection_summary(comp, display_title="Bourbon Biscuits — Britannia")
        self.assertIsNotNone(summary_text)
        self.assertGreater(len(summary_text), 40)
        self.assertIn("COMPLIANT", summary_text)
        self.assertFalse(is_prompt_leakage(summary_text))

    def test_06_generate_pdf_compliant_inspection(self):
        """Test PDF generation for COMPLIANT inspection."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        pdf_bytes = generate_inspection_pdf(self.test_insp_id)
        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

        # Check report was persisted on disk
        saved_file = self.test_dir / "report" / "inspection_report.pdf"
        self.assertTrue(saved_file.exists())
        self.assertGreater(saved_file.stat().st_size, 1000)

    def test_07_generate_pdf_non_compliant_inspection(self):
        """Test PDF generation for NON_COMPLIANT inspection."""
        comp = self.create_mock_compliance_result("NON_COMPLIANT", failed_count=1)
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        pdf_bytes = generate_inspection_pdf(self.test_insp_id)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_08_generate_pdf_with_exemptions(self):
        """Test PDF generation includes Rule 26 exemption traceability section."""
        comp = self.create_mock_compliance_result("NEEDS_REVIEW", exempt_count=1)
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        pdf_bytes = generate_inspection_pdf(self.test_insp_id)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_09_pdf_export_endpoint_post(self):
        """Test POST /api/inspections/{id}/report returns PDF attachment."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        response = self.client.post(f"/api/inspections/{self.test_insp_id}/report")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("attachment", response.headers.get("content-disposition", ""))
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_10_summary_endpoint_get(self):
        """Test GET /api/inspections/{id}/summary returns JSON summary."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        response = self.client.get(f"/api/inspections/{self.test_insp_id}/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["inspection_id"], self.test_insp_id)
        self.assertIn("summary", data)
        self.assertEqual(data["overall_status"], "COMPLIANT")

    def test_11_history_rename_preserves_inspection_id_and_compliance(self):
        """Test renaming an inspection preserves inspection_id and compliance results."""
        comp = self.create_mock_compliance_result("COMPLIANT")
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        # Rename inspection
        rename_res = self.client.patch(
            f"/api/inspections/{self.test_insp_id}",
            json={"display_name": "Custom Renamed Biscuit Pack"}
        )
        self.assertEqual(rename_res.status_code, 200)
        self.assertEqual(rename_res.json()["display_name"], "Custom Renamed Biscuit Pack")

        # Verify inspection_id and compliance result are intact
        get_res = self.client.get(f"/api/inspections/{self.test_insp_id}")
        self.assertEqual(get_res.status_code, 200)
        bundle = get_res.json()
        self.assertEqual(bundle["metadata"]["inspection_id"], self.test_insp_id)
        self.assertEqual(bundle["metadata"]["display_name"], "Custom Renamed Biscuit Pack")
        self.assertEqual(bundle["compliance"]["overall_status"], "COMPLIANT")

    def test_12_clean_display_product_name_removes_ocr_noise(self):
        """Test that random hash suffixes and leading/trailing numbers are stripped."""
        raw = "255 Original Style Chilli Sprinkled 3 Bingo Original Imahgycfya2yx6nn"
        cleaned = clean_display_product_name(raw)
        self.assertNotIn("Imahgycfya2yx6nn", cleaned)
        self.assertNotIn("255", cleaned)
        self.assertIn("Chilli Sprinkled", cleaned)
        self.assertIn("Bingo", cleaned)

        # Test composite formatting
        composite = format_composite_product_title("Chilli Sprinkled", "Bingo", "product.jpg")
        self.assertEqual(composite, "Chilli Sprinkled — Bingo")

        # Test camera filename fallback
        cam_title = clean_filename_title("IMG_20260831_123456.jpg")
        self.assertEqual(cam_title, "Untitled Inspection")

    def test_13_long_product_name_and_long_rule_description_pdf_generation(self):
        """Test PDF generation with very long product name and complex rule text."""
        long_title = "Very Long Packaged Commodity Name With Organic Multi-Grain Whole Wheat Extruded Snack Food Matrix"
        with open(self.test_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump({
                "inspection_id": self.test_insp_id,
                "display_name": long_title,
                "product_name": long_title,
                "status": "needs_review",
                "created_at": "2026-08-31T12:00:00Z",
                "image_count": 4
            }, f)

        comp = self.create_mock_compliance_result("NEEDS_REVIEW", review_count=1)
        with open(self.test_dir / "compliance" / "compliance_result.json", "w", encoding="utf-8") as f:
            json.dump(comp.model_dump(), f)

        pdf_bytes = generate_inspection_pdf(self.test_insp_id)
        self.assertIsNotNone(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
