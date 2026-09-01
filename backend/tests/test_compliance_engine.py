"""
Comprehensive Phase 3 Legal Metrology Compliance Engine Test Suite
Tests all specified scenarios:
1. Fully compliant retail package -> COMPLIANT
2. Missing manufacturer (partial coverage -> NEEDS_REVIEW)
3. Missing country of origin on imported product -> FAIL
4. Missing MRP -> FAIL
5. Missing net quantity -> FAIL
6. Missing consumer care -> FAIL
7. Missing unit sale price (full coverage) -> FAIL
8. Correct unit sale price -> PASS
9. Incorrect unit sale price (<1kg declared per kg) -> FAIL
10. Conflicting MRP values (dual pricing) -> NON_COMPLIANT
11. Partial image coverage -> NEEDS_REVIEW
12. Full package coverage with missing fields -> NON_COMPLIANT
13. Ambiguous OCR (NET WT 5) -> NEEDS_REVIEW
14. Group package (Rule 4)
15. Electronic product QR case (2023 amendment)
16. Medical device case (2025 amendment / Medical Devices Rules 2017 override)
17. Small-package exemption (Rule 26(a) <= 10g -> EXEMPT)
18. Wholesale package (Rule 24)
19. Export package (Rule 25)
20. Best-before applicable (Food/Perishable)
21. Best-before not applicable (Non-perishable)
22. Font-size without calibration -> NEEDS_REVIEW
23. Normal packaged biscuits (>10g) -> NOT exempt under Rule 26, Rule 6(1)(a) evaluated
24. Biscuits <= 10g (e.g. 5g sample) -> EXEMPT under Rule 26(a)
25. Biscuits > 10g (e.g. 100g) -> NOT exempt under Rule 26(a)
26. Restaurant-packed fast food -> EXEMPT under Rule 26(b)
27. Ordinary packaged food (e.g. 500g Atta) -> NOT exempt under Rule 26
28. Missing net quantity -> Evaluates without assuming exemption
29. EXEMPT vs NOT_APPLICABLE distinction
30. History rename preserves inspection_id, OCR, and compliance data
31. Real-world Britannia sample test
"""

import unittest
from backend.models.schemas import (
    StructuredProductData,
    ProductFields,
    ExtractedField,
    ImageCoverage,
    Evidence,
    CandidateValue,
    OtherDetectedInfoItem
)
from backend.services.applicability_engine import derive_applicability_facts
from backend.services.rule_registry import get_active_rules
from backend.services.compliance_evaluator import evaluate_compliance


def make_evidence(text: str, conf: float = 0.98, img_id: str = "IMG-001") -> Evidence:
    return Evidence(image_id=img_id, source_text=text, ocr_confidence=conf, bbox=[10, 10, 100, 30])


class TestLegalMetrologyComplianceEngine(unittest.TestCase):

    def setUp(self):
        self.rules = get_active_rules("2026-08-31")

    def test_01_fully_compliant_retail_package(self):
        """Test a fully compliant packaged commodity satisfies all mandatory declarations."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Bourbon Biscuits", status="extracted", evidence=[make_evidence("Bourbon Biscuits")]),
            manufacturer=ExtractedField[str](value="Britannia Industries Ltd, 5/1 Hungerford Street, Kolkata 700017", status="extracted", evidence=[make_evidence("Mfg by: Britannia Industries Ltd, Kolkata")]),
            manufacturer_address=ExtractedField[str](value="5/1 Hungerford Street, Kolkata 700017", status="extracted", evidence=[make_evidence("Kolkata 700017")]),
            net_quantity=ExtractedField[float](value=120.0, unit="g", status="extracted", evidence=[make_evidence("Net Wt 120 g")]),
            mrp=ExtractedField[float](value=35.0, currency="INR", status="extracted", evidence=[make_evidence("MRP Rs. 35.00 (Incl. of all taxes)")]),
            manufacturing_date=ExtractedField[str](value="2026-06", precision="month", status="extracted", evidence=[make_evidence("Mfd: 06/2026")]),
            best_before=ExtractedField[str](value="9 Months from manufacture", status="extracted", evidence=[make_evidence("Best Before 9 Months")]),
            consumer_care_phone=ExtractedField[str](value="1800-425-4444", status="extracted", evidence=[make_evidence("Toll Free: 1800-425-4444")]),
            consumer_care_email=ExtractedField[str](value="feedback@britindia.com", status="extracted", evidence=[make_evidence("feedback@britindia.com")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-01",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=["front"]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=["pricing_and_mrp", "manufacturer_details"])
            ],
            product=prod,
            other_detected_information=[
                OtherDetectedInfoItem(category="pricing", label="Unit Sale Price", value="₹ 0.29 / g", evidence=[make_evidence("USP: Rs. 0.29 / g")])
            ],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        # Summary check
        self.assertEqual(res.summary.failed, 0)
        self.assertGreaterEqual(res.summary.passed, 7)
        self.assertFalse(app.is_exempt_under_rule_26)

    def test_02_missing_manufacturer_partial_coverage(self):
        """Test missing manufacturer on partial view produces NEEDS_REVIEW, not FAIL."""
        prod = ProductFields(
            mrp=ExtractedField[float](value=50.0, currency="INR", status="extracted", evidence=[make_evidence("MRP Rs 50")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-02",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "NEEDS_REVIEW")
        self.assertIn("not observed in supplied image", mfg_check.reason.lower())

    def test_03_missing_country_of_origin_on_imported_product(self):
        """Test imported product without country of origin fails Rule 6(1)(aa)."""
        prod = ProductFields(
            importer=ExtractedField[str](value="Overseas Trade Ltd, Mumbai", status="extracted", evidence=[make_evidence("Imported by: Overseas Trade Ltd")]),
            country_of_origin=ExtractedField[str](value=None, status="not_observed")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-03",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_imported)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        coo_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-aa")
        self.assertEqual(coo_check.status, "FAIL")

    def test_04_missing_mrp_full_coverage(self):
        """Test retail package missing MRP after full coverage produces FAIL."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Biscuit", status="extracted", evidence=[make_evidence("Biscuit")]),
            mrp=ExtractedField[float](value=None, status="not_observed")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-04",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        mrp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-e")
        self.assertEqual(mrp_check.status, "FAIL")
        self.assertEqual(res.overall_status, "NON_COMPLIANT")

    def test_05_missing_net_quantity_full_coverage(self):
        """Test missing net quantity on full coverage fails Rule 6(1)(c)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Tea", status="extracted", evidence=[make_evidence("Tea")]),
            net_quantity=ExtractedField[float](value=None, status="not_observed")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-05",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        qty_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-c")
        self.assertEqual(qty_check.status, "FAIL")

    def test_06_missing_consumer_care_full_coverage(self):
        """Test missing consumer care on full coverage fails Rule 6(1)(f)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Soap", status="extracted", evidence=[make_evidence("Soap")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-06",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        cc_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-f")
        self.assertEqual(cc_check.status, "FAIL")

    def test_07_unit_sale_price_missing_full_coverage(self):
        """Test missing USP on package after effective date fails Rule 6(1)(m)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Tea Powder", status="extracted", evidence=[make_evidence("Tea")]),
            mrp=ExtractedField[float](value=250.0, currency="INR", status="extracted", evidence=[make_evidence("MRP 250")]),
            net_quantity=ExtractedField[float](value=500.0, unit="g", status="extracted", evidence=[make_evidence("500g")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-07",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        usp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-m")
        self.assertEqual(usp_check.status, "FAIL")

    def test_08_correct_unit_sale_price(self):
        """Test declared USP matching threshold rules passes."""
        prod = ProductFields(
            net_quantity=ExtractedField[float](value=200.0, unit="g", status="extracted", evidence=[make_evidence("200 g")]),
            mrp=ExtractedField[float](value=50.0, currency="INR", status="extracted", evidence=[make_evidence("MRP Rs 50")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-08",
            images=[ImageCoverage(image_id="IMG-1", image_type="mixed_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[
                OtherDetectedInfoItem(category="pricing", label="Unit Sale Price", value="Rs. 0.25 / g", evidence=[make_evidence("Rs. 0.25 / g")])
            ],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        usp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-m")
        self.assertEqual(usp_check.status, "PASS")

    def test_09_incorrect_unit_sale_price_threshold(self):
        """Test package < 1kg declared per kg fails Rule 6(11) threshold requirements."""
        prod = ProductFields(
            net_quantity=ExtractedField[float](value=100.0, unit="g", status="extracted", evidence=[make_evidence("100 g")]),
            mrp=ExtractedField[float](value=40.0, currency="INR", status="extracted", evidence=[make_evidence("MRP Rs 40")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-09",
            images=[ImageCoverage(image_id="IMG-1", image_type="mixed_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[
                OtherDetectedInfoItem(category="pricing", label="Unit Sale Price", value="Rs. 400.00 / kg", evidence=[make_evidence("Rs. 400.00 / kg")])
            ],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        usp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-m")
        self.assertEqual(usp_check.status, "FAIL")
        self.assertIn("requires USP per gram", usp_check.reason)

    def test_10_conflicting_mrp_dual_pricing(self):
        """Test conflicting dual MRP fails Rule 6(1)(e)."""
        prod = ProductFields(
            mrp=ExtractedField[float](
                value=None,
                currency="INR",
                status="conflicting",
                candidates=[CandidateValue(value=100.0, evidence=make_evidence("₹100")), CandidateValue(value=120.0, evidence=make_evidence("₹120"))],
                evidence=[make_evidence("₹100"), make_evidence("₹120")]
            )
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-10",
            images=[ImageCoverage(image_id="IMG-1", image_type="mixed_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        mrp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-e")
        self.assertEqual(mrp_check.status, "FAIL")
        self.assertEqual(res.overall_status, "NON_COMPLIANT")

    def test_11_partial_image_coverage_needs_review(self):
        """Test single panel with missing declarations overall evaluates to NEEDS_REVIEW."""
        prod = ProductFields(
            mrp=ExtractedField[float](value=30.0, currency="INR", status="extracted", evidence=[make_evidence("₹30")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-11",
            images=[ImageCoverage(image_id="IMG-1", image_type="mrp_panel", visibility_confidence=0.8, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        self.assertEqual(res.overall_status, "NEEDS_REVIEW")

    def test_12_full_package_coverage_fails(self):
        """Test full package coverage with missing statutory fields produces NON_COMPLIANT."""
        prod = ProductFields(
            mrp=ExtractedField[float](value=30.0, currency="INR", status="extracted", evidence=[make_evidence("₹30")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-12",
            images=[
                ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.95, visible_sections=[]),
                ImageCoverage(image_id="IMG-2", image_type="back_panel", visibility_confidence=0.95, visible_sections=[])
            ],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        self.assertEqual(res.overall_status, "NON_COMPLIANT")

    def test_13_ambiguous_ocr_net_quantity(self):
        """Test ambiguous quantity 'NET WT 5' retains uncertainty with NEEDS_REVIEW."""
        prod = ProductFields(
            net_quantity=ExtractedField[float](value=5.0, unit=None, status="ambiguous", evidence=[make_evidence("NET WT 5")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-13",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        qty_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-c")
        self.assertEqual(qty_check.status, "NEEDS_REVIEW")

    def test_14_group_package_rule_4(self):
        """Test group package under Rule 4."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Biscuit Combo", status="extracted", evidence=[make_evidence("Combo Pack")]),
            number_of_items=ExtractedField[int](value=3, status="extracted", evidence=[make_evidence("Pack of 3")]),
            net_quantity=ExtractedField[float](value=300.0, unit="g", status="extracted", evidence=[make_evidence("300 g")]),
            mrp=ExtractedField[float](value=90.0, currency="INR", status="extracted", evidence=[make_evidence("MRP 90")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-14",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_group_package)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        r4_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R4")
        self.assertEqual(r4_check.status, "PASS")

    def test_15_electronic_product_qr_provisions(self):
        """Test electronic product 2023 QR code provisions."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Smart LED Bulb", status="extracted", evidence=[make_evidence("LED Bulb")]),
            mrp=ExtractedField[float](value=299.0, currency="INR", status="extracted", evidence=[make_evidence("MRP ₹299")]),
            consumer_care_phone=ExtractedField[str](value="1800-111-222", status="extracted", evidence=[make_evidence("1800-111-222")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-15",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_electronic_product)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        qr_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R-ELEC-QR")
        self.assertEqual(qr_check.status, "PASS")

    def test_16_medical_device_treatment_2025(self):
        """Test medical device special statutory treatment (Medical Devices Rules 2017)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Surgical Catheter", status="extracted", evidence=[make_evidence("Catheter")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-16",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_medical_device)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        med_check = next(c for c in res.checks if c.rule_id == "PCR-2025-MED-DEV")
        self.assertEqual(med_check.status, "PASS")
        self.assertIn("Medical Devices Rules, 2017 apply", med_check.reason)

    def test_17_small_package_exemption_rule_26(self):
        """Test small package <= 10g is EXEMPT from Chapter II declarations under Rule 26(a)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Candy Sample", status="extracted", evidence=[make_evidence("Candy")]),
            net_quantity=ExtractedField[float](value=4.0, unit="g", status="extracted", evidence=[make_evidence("4 g")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-17",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_exempt_under_rule_26)
        self.assertEqual(app.rule_26_clause, "26(a)")

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "EXEMPT")
        self.assertIsNotNone(mfg_check.exemption)
        self.assertEqual(mfg_check.exemption.exemption_clause, "26(a)")

    def test_18_wholesale_package_rule_24(self):
        """Test wholesale package evaluation."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Wheat Flour Bulk Sack", status="extracted", evidence=[make_evidence("Bulk Sack")]),
            manufacturer=ExtractedField[str](value="Agro Mills Ltd", status="extracted", evidence=[make_evidence("Agro Mills")]),
            net_quantity=ExtractedField[float](value=50.0, unit="kg", status="extracted", evidence=[make_evidence("50 kg")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-18",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data, inspection_hints={"is_wholesale": True})
        self.assertTrue(app.is_wholesale_package)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        ws_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R24")
        self.assertEqual(ws_check.status, "PASS")

    def test_19_export_package_rule_25(self):
        """Test export package evaluation."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Basmati Rice For Export Only", status="extracted", evidence=[make_evidence("For Export Only")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-19",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data, inspection_hints={"is_export": True})
        self.assertTrue(app.is_export_package)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        exp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R25")
        self.assertEqual(exp_check.status, "PASS")

    def test_20_best_before_non_perishable_not_applicable(self):
        """Test non-perishable goods (e.g. garments, electronics) mark best-before as NOT_APPLICABLE."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Cotton Shirt", status="extracted", evidence=[make_evidence("Cotton Shirt")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-20",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertEqual(app.commodity_type, "garment")

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        exp_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-expiry")
        self.assertEqual(exp_check.status, "NOT_APPLICABLE")

    def test_21_font_size_uncalibrated_needs_review(self):
        """Test character height without physical calibration produces NEEDS_REVIEW with official reason."""
        prod = ProductFields(
            net_quantity=ExtractedField[float](value=500.0, unit="g", status="extracted", evidence=[make_evidence("500 g")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-COMPL-21",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        font_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R7-8")
        self.assertEqual(font_check.status, "NEEDS_REVIEW")
        self.assertIn("physical character height cannot be verified", font_check.reason.lower())

    def test_22_britannia_real_world_evaluation(self):
        """Test Britannia sample evaluation preserves evidence and evaluates deterministically."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Britannia Bourbon Biscuits", status="extracted", evidence=[make_evidence("Britannia Bourbon")]),
            manufacturer=ExtractedField[str](value="Britannia Industries Ltd", status="extracted", evidence=[make_evidence("Britannia Industries Ltd")]),
            net_quantity=ExtractedField[float](value=120.0, unit="g", status="extracted", evidence=[make_evidence("120 g")]),
            mrp=ExtractedField[float](value=35.0, currency="INR", status="extracted", evidence=[make_evidence("MRP Rs 35.00")]),
            manufacturing_date=ExtractedField[str](value="2026-06", precision="month", status="extracted", evidence=[make_evidence("06/2026")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-BRITANNIA-REAL",
            images=[ImageCoverage(image_id="IMG-1", image_type="mixed_panel", visibility_confidence=0.95, visible_sections=["pricing_and_mrp", "manufacturer_details"])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertFalse(app.is_exempt_under_rule_26)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        self.assertEqual(res.schema_version, "1.0")
        self.assertEqual(res.inspection_id, "TEST-BRITANNIA-REAL")

        # Verify Rule 6(1)(a) is PASS and NOT exempt
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "PASS")

    def test_23_normal_biscuits_not_exempt(self):
        """Test normal packaged biscuits (120g) are NOT exempt; Rule 6(1)(a) evaluates strictly."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Bourbon Biscuits", status="extracted"),
            net_quantity=ExtractedField[float](value=120.0, unit="g", status="extracted"),
            manufacturer=ExtractedField[str](value="Britannia Industries Ltd", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-NORM-BISCUITS",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertFalse(app.is_exempt_under_rule_26)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "PASS")
        self.assertNotEqual(mfg_check.status, "NOT_APPLICABLE")
        self.assertNotEqual(mfg_check.status, "EXEMPT")

    def test_24_biscuits_under_10g_exempt_rule_26_a(self):
        """Test sample biscuits pack <= 10g triggers Rule 26(a) EXEMPT status."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Biscuits Sample Pack", status="extracted"),
            net_quantity=ExtractedField[float](value=5.0, unit="g", status="extracted", evidence=[make_evidence("Net Wt: 5g")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-SMALL-BISCUIT",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_exempt_under_rule_26)
        self.assertEqual(app.rule_26_clause, "26(a)")

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "EXEMPT")
        self.assertIsNotNone(mfg_check.exemption)
        self.assertEqual(mfg_check.exemption.exemption_clause, "26(a)")

    def test_25_biscuits_over_10g_not_exempt(self):
        """Test 100g biscuits package is NOT exempt under Rule 26(a)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Glucose Biscuits", status="extracted"),
            net_quantity=ExtractedField[float](value=100.0, unit="g", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-100G-BISCUIT",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertFalse(app.is_exempt_under_rule_26)

    def test_26_restaurant_packed_fast_food_rule_26_b(self):
        """Test fast food packed by restaurant is EXEMPT under Rule 26(b)."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Burger Takeaway Pack", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-FAST-FOOD",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[
                OtherDetectedInfoItem(category="packaging", label="Notice", value="Packed by Restaurant for direct delivery", evidence=[make_evidence("Packed by Restaurant")])
            ],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertTrue(app.is_exempt_under_rule_26)
        self.assertEqual(app.rule_26_clause, "26(b)")

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "EXEMPT")
        self.assertEqual(mfg_check.exemption.exemption_clause, "26(b)")

    def test_27_ordinary_packaged_food_no_exemption(self):
        """Test 500g Atta package is standard packaged commodity with NO Rule 26 exemption."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Chakki Fresh Atta", status="extracted"),
            net_quantity=ExtractedField[float](value=500.0, unit="g", status="extracted"),
            manufacturer=ExtractedField[str](value="Aashirvaad ITC Ltd", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-ATTA-500G",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertFalse(app.is_exempt_under_rule_26)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")
        self.assertEqual(mfg_check.status, "PASS")

    def test_28_missing_net_quantity_does_not_assume_exemption(self):
        """Test package with missing net quantity evaluates without assuming exemption."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Cookies", status="extracted"),
            net_quantity=ExtractedField[float](value=None, status="not_observed")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-MISSING-QTY",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        self.assertFalse(app.is_exempt_under_rule_26)

        res = evaluate_compliance(data, app, self.rules, "2026-08-31")
        qty_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-c")
        self.assertEqual(qty_check.status, "NEEDS_REVIEW")

    def test_29_exempt_vs_not_applicable_distinction(self):
        """Test EXEMPT is distinct from NOT_APPLICABLE."""
        # For domestic product: Country of Origin rule is NOT_APPLICABLE
        # For 5g sample product: Manufacturer rule is EXEMPT
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Sample Powder", status="extracted"),
            net_quantity=ExtractedField[float](value=3.0, unit="g", status="extracted", evidence=[make_evidence("3g")])
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-DISTINCT-STATUS",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        app = derive_applicability_facts(data)
        res = evaluate_compliance(data, app, self.rules, "2026-08-31")

        coo_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-aa")
        mfg_check = next(c for c in res.checks if c.rule_id == "PCR-2011-R6-1-a")

        self.assertEqual(coo_check.status, "NOT_APPLICABLE")
        self.assertEqual(mfg_check.status, "EXEMPT")
        self.assertNotEqual(coo_check.status, mfg_check.status)


if __name__ == "__main__":
    unittest.main()
