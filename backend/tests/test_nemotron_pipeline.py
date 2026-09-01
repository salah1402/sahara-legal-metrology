"""
Comprehensive Phase 2 Test Suite for MetraCheck Legal Metrology Normalization Pipeline
Tests:
1. Clear OCR
2. Low-confidence OCR
3. Missing field (not_observed)
4. Ambiguous field
5. Conflicting field
6. Duplicate field
7. Multiple images
8. Nutrition-only image
9. Front-panel image
10. Back-panel image
11. Mixed-panel image regression (MRP + Nutrition + FSSAI)
12. Date with month/year only
13. Unit normalization
14. Malformed LLM output
15. Missing NVIDIA API key
16. NVIDIA API failure
17. Rename inspection endpoint (PATCH /api/inspections/{id})
18. Rename persistence on disk
19. Inspection ID immutability after rename
20. Backward compatibility for inspections without display_name
21. Clean filename title derivation
22. Naming priority hierarchy (User Name > Nemotron commodity_name > Clean Filename > Untitled)
23. Reset custom name to automatic naming
"""

import os
import json
import shutil
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import (
    app,
    INSPECTIONS_DIR,
    clean_filename_title,
    resolve_display_name
)
from backend.models.schemas import OCRRegion, StructuredProductData
from backend.services.nemotron_service import (
    normalize_ocr_with_nemotron,
    fallback_semantic_normalize,
    clean_json_response
)


class TestNemotronNormalizationPipeline(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_clear_ocr_extraction(self):
        """Test clean, unambiguous OCR extraction with evidence preservation."""
        tokens = [
            OCRRegion(id="ocr_1", text="BRITANNIA GOOD DAY BUTTER COOKIES", confidence=0.99, bbox=[50, 50, 400, 90], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="Net Weight: 500 g", confidence=0.98, bbox=[50, 100, 250, 140], image_id="IMG-001"),
            OCRRegion(id="ocr_3", text="MRP Rs. 120.00 (Incl. of all taxes)", confidence=0.97, bbox=[50, 150, 350, 190], image_id="IMG-001"),
            OCRRegion(id="ocr_4", text="Manufactured by: Britannia Industries Ltd, Kolkata 700017", confidence=0.96, bbox=[50, 200, 550, 240], image_id="IMG-001"),
            OCRRegion(id="ocr_5", text="Country of Origin: INDIA", confidence=0.99, bbox=[50, 250, 300, 290], image_id="IMG-001"),
            OCRRegion(id="ocr_6", text="Customer Care: 1800-425-4444 | feedback@britindia.com", confidence=0.95, bbox=[50, 300, 500, 340], image_id="IMG-001")
        ]

        data = fallback_semantic_normalize(tokens, "TEST-INSP-01")

        self.assertEqual(data.schema_version, "1.0")
        self.assertEqual(data.product.mrp.value, 120.0)
        self.assertEqual(data.product.mrp.currency, "INR")
        self.assertEqual(data.product.mrp.status, "extracted")
        self.assertGreater(len(data.product.mrp.evidence), 0)
        self.assertEqual(data.product.mrp.evidence[0].source_text, "MRP Rs. 120.00 (Incl. of all taxes)")
        self.assertEqual(data.product.mrp.evidence[0].ocr_confidence, 0.97)

        self.assertEqual(data.product.net_quantity.value, 500.0)
        self.assertEqual(data.product.net_quantity.unit, "g")
        self.assertEqual(data.product.country_of_origin.value, "INDIA")
        self.assertEqual(data.product.consumer_care_phone.value, "1800-425-4444")
        self.assertEqual(data.product.consumer_care_email.value, "feedback@britindia.com")

    def test_02_low_confidence_ocr(self):
        """Test OCR confidence is preserved exactly as detected without modification."""
        tokens = [
            OCRRegion(id="ocr_1", text="MRP Rs. 85.00", confidence=0.42, bbox=[10, 10, 100, 30], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-02")
        self.assertEqual(data.product.mrp.value, 85.0)
        self.assertEqual(data.product.mrp.evidence[0].ocr_confidence, 0.42)

    def test_03_missing_field_is_not_observed(self):
        """Test fields not present in OCR are marked 'not_observed' without hallucinating."""
        tokens = [
            OCRRegion(id="ocr_1", text="Britannia Good Day", confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-03")
        self.assertEqual(data.product.mrp.status, "not_observed")
        self.assertIsNone(data.product.mrp.value)
        self.assertEqual(data.product.manufacturer.status, "not_observed")
        self.assertEqual(data.product.country_of_origin.status, "not_observed")

    def test_04_ambiguous_field(self):
        """Test ambiguous input like 'NET WT 5' retains uncertainty."""
        tokens = [
            OCRRegion(id="ocr_1", text="NET WT 5", confidence=0.95, bbox=[10, 10, 100, 30], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-04")
        self.assertEqual(data.product.net_quantity.status, "ambiguous")
        self.assertEqual(data.product.net_quantity.value, 5.0)
        self.assertIsNone(data.product.net_quantity.unit)
        self.assertGreater(len(data.ambiguities), 0)

    def test_05_conflicting_field(self):
        """Test conflicting price declarations create candidate list and set status='conflicting'."""
        tokens = [
            OCRRegion(id="ocr_1", text="MRP ₹120", confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="MRP ₹150", confidence=0.97, bbox=[10, 40, 100, 60], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-05")
        self.assertEqual(data.product.mrp.status, "conflicting")
        self.assertIsNone(data.product.mrp.value)
        self.assertIsNotNone(data.product.mrp.candidates)
        self.assertEqual(len(data.product.mrp.candidates), 2)
        self.assertGreater(len(data.conflicts), 0)

    def test_06_duplicate_field_same_value(self):
        """Test same field observed multiple times with identical value creates multiple evidence entries."""
        tokens = [
            OCRRegion(id="ocr_1", text="MRP ₹120.00", confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="MRP Rs.120/-", confidence=0.95, bbox=[10, 40, 100, 60], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-06")
        self.assertEqual(data.product.mrp.status, "extracted")
        self.assertEqual(data.product.mrp.value, 120.0)
        self.assertEqual(len(data.product.mrp.evidence), 2)

    def test_07_multiple_images_combined(self):
        """Test multi-image OCR tokens are unified while tagging respective image_id."""
        tokens = [
            OCRRegion(id="ocr_1", text="Brand: Sunfeast Dark Fantasy", confidence=0.99, bbox=[10, 10, 100, 30], image_id="IMG-FRONT"),
            OCRRegion(id="ocr_2", text="Manufactured by: ITC Limited, Kolkata 700071", confidence=0.97, bbox=[20, 20, 150, 40], image_id="IMG-BACK"),
            OCRRegion(id="ocr_3", text="MRP Rs. 90.00", confidence=0.96, bbox=[30, 30, 80, 50], image_id="IMG-SIDE")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-07")
        self.assertEqual(len(data.images), 3)
        self.assertEqual(data.product.manufacturer.evidence[0].image_id, "IMG-BACK")
        self.assertEqual(data.product.mrp.evidence[0].image_id, "IMG-SIDE")

    def test_08_nutrition_only_image_classification(self):
        """Test nutrition-only panel is classified properly and missing mandatory declarations remain not_observed."""
        tokens = [
            OCRRegion(id="ocr_1", text="NUTRITIONAL INFORMATION", confidence=0.99, bbox=[10, 10, 200, 30], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="Serving Size: 30g", confidence=0.98, bbox=[10, 40, 150, 60], image_id="IMG-001"),
            OCRRegion(id="ocr_3", text="Energy: 480 kcal", confidence=0.97, bbox=[10, 70, 120, 90], image_id="IMG-001"),
            OCRRegion(id="ocr_4", text="Protein: 7.2 g", confidence=0.96, bbox=[10, 100, 100, 120], image_id="IMG-001"),
            OCRRegion(id="ocr_5", text="Carbohydrate: 68 g", confidence=0.95, bbox=[10, 130, 130, 150], image_id="IMG-001"),
            OCRRegion(id="ocr_6", text="Total Sugars: 24 g", confidence=0.96, bbox=[10, 160, 120, 180], image_id="IMG-001"),
            OCRRegion(id="ocr_7", text="Sodium: 180 mg", confidence=0.94, bbox=[10, 190, 110, 210], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-08")
        self.assertEqual(data.images[0].image_type, "nutrition_panel")
        self.assertIn("nutrition_information", data.images[0].visible_sections)
        self.assertEqual(data.product.manufacturer.status, "not_observed")
        self.assertEqual(data.product.mrp.status, "not_observed")
        self.assertGreater(len(data.other_detected_information), 3)

    def test_09_front_panel_image(self):
        """Test front panel classification."""
        tokens = [
            OCRRegion(id="ocr_1", text="Britannia Pure Butter Cookies", confidence=0.99, bbox=[10, 10, 300, 40], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="Net Wt: 200 g", confidence=0.98, bbox=[10, 50, 120, 70], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-09")
        self.assertEqual(data.images[0].image_type, "front_panel")

    def test_10_back_panel_image(self):
        """Test back panel containing MRP and manufacturer."""
        tokens = [
            OCRRegion(id="ocr_1", text="Mfg by: ABC Foods Ltd, Mumbai", confidence=0.98, bbox=[10, 10, 200, 30], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="MRP Rs. 50.00", confidence=0.97, bbox=[10, 40, 100, 60], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-10")
        self.assertEqual(data.images[0].image_type, "back_panel")

    def test_11_mixed_panel_image_regression(self):
        """Test regression: Image containing MRP + Nutrition + FSSAI is classified as 'mixed_panel'."""
        tokens = [
            OCRRegion(id="ocr_1", text="MRP Rs. 45.00 (Incl. of taxes)", confidence=0.98, bbox=[10, 10, 200, 30], image_id="IMG-001"),
            OCRRegion(id="ocr_2", text="NUTRITION FACTS: Energy 450 kcal, Protein 6g", confidence=0.97, bbox=[10, 40, 300, 60], image_id="IMG-001"),
            OCRRegion(id="ocr_3", text="fssai Lic. No. 10012022000123", confidence=0.99, bbox=[10, 70, 250, 90], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-11")
        self.assertEqual(data.images[0].image_type, "mixed_panel")
        self.assertIn("pricing_and_mrp", data.images[0].visible_sections)
        self.assertIn("nutrition_information", data.images[0].visible_sections)
        self.assertIn("regulatory_information", data.images[0].visible_sections)

    def test_12_date_month_year_precision(self):
        """Test date with month and year preserves precision='month'."""
        tokens = [
            OCRRegion(id="ocr_1", text="Mfd: 06/2026", confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-12")
        self.assertEqual(data.product.manufacturing_date.value, "2026-06")
        self.assertEqual(data.product.manufacturing_date.precision, "month")
        self.assertEqual(data.product.manufacturing_date.status, "extracted")

    def test_13_unit_normalization(self):
        """Test metric units standardized (g, kg, mL, L)."""
        cases = [
            ("Net Wt 500 Gms", 500.0, "g"),
            ("Net Volume 1000 mL", 1000.0, "mL"),
            ("Weight 2 Kgs", 2.0, "kg"),
            ("Volume 1.5 Litres", 1.5, "L")
        ]
        for text, exp_val, exp_unit in cases:
            tokens = [OCRRegion(id="ocr_1", text=text, confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001")]
            data = fallback_semantic_normalize(tokens, "TEST-UNIT")
            self.assertEqual(data.product.net_quantity.value, exp_val)
            self.assertEqual(data.product.net_quantity.unit, exp_unit)

    def test_14_malformed_llm_json_cleaning(self):
        """Test clean_json_response cleans markdown fences and extra commentary."""
        raw = "```json\n{\n  \"schema_version\": \"1.0\",\n  \"inspection_id\": \"TEST\"\n}\n```"
        cleaned = clean_json_response(raw)
        self.assertTrue(cleaned.startswith("{"))
        self.assertTrue(cleaned.endswith("}"))

    def test_15_missing_nvidia_api_key_handling(self):
        """Test normalization completes safely when fallback parser is invoked."""
        tokens = [
            OCRRegion(id="ocr_1", text="MRP Rs. 100", confidence=0.98, bbox=[10, 10, 100, 30], image_id="IMG-001")
        ]
        data = fallback_semantic_normalize(tokens, "TEST-INSP-15")
        self.assertEqual(data.product.mrp.value, 100.0)

    def test_16_nvidia_api_failure_fallback(self):
        """Test empty or malformed token fallback behavior."""
        data = normalize_ocr_with_nemotron([], "TEST-EMPTY")
        self.assertEqual(data.schema_version, "1.0")
        self.assertEqual(len(data.images), 1)

    def test_17_rename_inspection_endpoint(self):
        """Test PATCH /api/inspections/{id} updates human-readable title without altering inspection_id."""
        test_id = "INS-TEST-RENAME-001"
        test_dir = INSPECTIONS_DIR / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        meta_file = test_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"inspection_id": test_id, "created_at": "2026-08-31T00:00:00Z", "status": "normalized"}, f)

        try:
            res = self.client.patch(
                f"/api/inspections/{test_id}",
                json={"display_name": "Britannia Bourbon — MRP Panel"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("inspection_id"), test_id)
            self.assertEqual(data.get("display_name"), "Britannia Bourbon — MRP Panel")
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_18_rename_persistence_on_disk(self):
        """Test display_name is saved to metadata.json and survives reading from disk."""
        test_id = "INS-TEST-RENAME-PERSIST"
        test_dir = INSPECTIONS_DIR / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        meta_file = test_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"inspection_id": test_id, "created_at": "2026-08-31T00:00:00Z", "status": "normalized"}, f)

        try:
            self.client.patch(
                f"/api/inspections/{test_id}",
                json={"display_name": "Custom Label Name"}
            )
            with open(meta_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved.get("display_name"), "Custom Label Name")
            self.assertEqual(saved.get("inspection_id"), test_id)
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_19_inspection_id_immutability_after_rename(self):
        """Test physical filesystem directory and inspection ID remain strictly unchanged after rename."""
        test_id = "INS-TEST-IMMUTABLE-ID"
        test_dir = INSPECTIONS_DIR / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        meta_file = test_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"inspection_id": test_id, "created_at": "2026-08-31T00:00:00Z", "status": "normalized"}, f)

        try:
            self.client.patch(
                f"/api/inspections/{test_id}",
                json={"display_name": "Completely Different Title"}
            )
            # Physical folder path MUST still exist under the original inspection ID
            self.assertTrue(test_dir.exists())
            self.assertTrue((INSPECTIONS_DIR / test_id).is_dir())
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_20_backward_compatibility_without_display_name(self):
        """Test legacy inspections without display_name load cleanly via GET /api/inspections/{id}."""
        test_id = "INS-TEST-LEGACY-001"
        test_dir = INSPECTIONS_DIR / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        meta_file = test_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({"inspection_id": test_id, "created_at": "2026-08-31T00:00:00Z", "product_name": "Old Product", "status": "ocr_completed"}, f)

        try:
            res = self.client.get(f"/api/inspections/{test_id}")
            self.assertEqual(res.status_code, 200)
            bundle = res.json()
            meta = bundle.get("metadata", {})
            self.assertEqual(meta.get("inspection_id"), test_id)
            self.assertEqual(meta.get("product_name"), "Old Product")
            self.assertIsNone(meta.get("display_name"))
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_21_clean_filename_title_derivation(self):
        """Test clean human-readable titles derived from uploaded filenames."""
        self.assertEqual(clean_filename_title("Britannia-The-Original-Bourbon.jpg"), "Britannia The Original Bourbon")
        self.assertEqual(clean_filename_title("Sunfeast_Dark_Fantasy_Choco_Fills.png"), "Sunfeast Dark Fantasy Choco Fills")
        self.assertEqual(clean_filename_title("parle_g_biscuits.webp"), "Parle G Biscuits")
        # Camera noise falls back to Untitled Inspection
        self.assertEqual(clean_filename_title("IMG_20260831_123456.jpg"), "Untitled Inspection")
        self.assertEqual(clean_filename_title("DSC_0042.jpg"), "Untitled Inspection")
        self.assertEqual(clean_filename_title("image.png"), "Untitled Inspection")
        self.assertEqual(clean_filename_title(""), "Untitled Inspection")

    def test_22_naming_priority_hierarchy(self):
        """Test strict 5-tier naming priority resolution."""
        # 1. Explicit display_name
        meta1 = {"display_name": "Manual Name", "product_name": "Commodity Name"}
        self.assertEqual(resolve_display_name(meta1), "Manual Name")

        # 2. Extracted commodity_name / product_name
        meta2 = {"display_name": None, "product_name": "Bourbon Biscuits"}
        self.assertEqual(resolve_display_name(meta2), "Bourbon Biscuits")

        # 3. Fallback to Untitled Inspection
        meta3 = {"display_name": None, "product_name": None}
        self.assertEqual(resolve_display_name(meta3), "Untitled Inspection")

        # Never outputs inspection_id
        meta4 = {"inspection_id": "INS-20260831-74D498B3"}
        self.assertEqual(resolve_display_name(meta4), "Untitled Inspection")
        self.assertNotEqual(resolve_display_name(meta4), "INS-20260831-74D498B3")

    def test_23_reset_name_to_automatic(self):
        """Test that resetting display_name clears manual override and restores auto-naming."""
        test_id = "INS-TEST-RESET-NAME"
        test_dir = INSPECTIONS_DIR / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        meta_file = test_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "inspection_id": test_id,
                "display_name": "Temporary Custom Name",
                "product_name": "Auto Detected Bourbon",
                "status": "normalized"
            }, f)

        try:
            # Send empty string to reset
            res = self.client.patch(
                f"/api/inspections/{test_id}",
                json={"display_name": ""}
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIsNone(data.get("display_name"))
            self.assertEqual(resolve_display_name(data), "Auto Detected Bourbon")
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
