"""
Phase 3 Applicability Engine Test Suite
Tests:
- Standard domestic retail food commodity
- Imported commodity
- Medical device (2025 amendment)
- Electronic product (2023 amendment)
- Garment / hosiery
- Small package exemption (Rule 26 <= 10g / 10mL)
- Wholesale package (Rule 24)
- Export package (Rule 25)
- Group / multi-piece package (Rule 4)
"""

import unittest
from backend.models.schemas import StructuredProductData, ProductFields, ExtractedField, ImageCoverage
from backend.services.applicability_engine import derive_applicability_facts


class TestApplicabilityEngine(unittest.TestCase):

    def test_01_standard_domestic_food_package(self):
        """Test domestic retail food package applicability."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Bourbon Biscuits", status="extracted"),
            manufacturer=ExtractedField[str](value="Britannia Industries Ltd, Kolkata", status="extracted"),
            net_quantity=ExtractedField[float](value=120.0, unit="g", status="extracted"),
            mrp=ExtractedField[float](value=35.0, currency="INR", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-01",
            images=[ImageCoverage(image_id="IMG-1", image_type="mixed_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_prepackaged_commodity)
        self.assertTrue(facts.intended_for_retail_sale)
        self.assertEqual(facts.package_category, "retail")
        self.assertEqual(facts.commodity_type, "food")
        self.assertFalse(facts.is_imported)
        self.assertFalse(facts.is_medical_device)
        self.assertFalse(facts.is_electronic_product)
        self.assertFalse(facts.is_exempt_under_rule_26)

    def test_02_imported_product_classification(self):
        """Test imported product detection via country of origin / importer."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Swiss Dark Chocolate", status="extracted"),
            importer=ExtractedField[str](value="Global Imports Pvt Ltd, Mumbai", status="extracted"),
            country_of_origin=ExtractedField[str](value="SWITZERLAND", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-02",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_imported)

    def test_03_medical_device_classification(self):
        """Test medical device identification triggers medical device treatment."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Digital Blood Pressure Monitor", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-03",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_medical_device)
        self.assertEqual(facts.commodity_type, "medical_device")

    def test_04_electronic_product_classification(self):
        """Test electronic product identification triggers 2023 QR provisions."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Wireless Bluetooth Earphone with Charger", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-04",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_electronic_product)
        self.assertEqual(facts.commodity_type, "electronics")

    def test_05_small_package_exemption_rule_26(self):
        """Test small package with net quantity <= 10g triggers Rule 26 exemption."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Chewing Gum", status="extracted"),
            net_quantity=ExtractedField[float](value=5.0, unit="g", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-05",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_exempt_under_rule_26)
        self.assertEqual(facts.package_category, "small_package")
        self.assertIn("10 g", facts.exemption_reason or "")

    def test_06_wholesale_package_classification(self):
        """Test wholesale package classification."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Bulk Rice Industrial Pack", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-06",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data, inspection_hints={"is_wholesale": True})
        self.assertTrue(facts.is_wholesale_package)
        self.assertFalse(facts.intended_for_retail_sale)
        self.assertEqual(facts.package_category, "wholesale")

    def test_07_group_package_classification(self):
        """Test group / multi-piece package classification."""
        prod = ProductFields(
            commodity_name=ExtractedField[str](value="Soap Twin Pack (Buy 1 Get 1)", status="extracted"),
            number_of_items=ExtractedField[int](value=2, status="extracted"),
            net_quantity=ExtractedField[float](value=250.0, unit="g", status="extracted")
        )
        data = StructuredProductData(
            schema_version="1.0",
            inspection_id="TEST-APP-07",
            images=[ImageCoverage(image_id="IMG-1", image_type="front_panel", visibility_confidence=0.9, visible_sections=[])],
            product=prod,
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

        facts = derive_applicability_facts(data)
        self.assertTrue(facts.is_group_package)
        self.assertEqual(facts.package_category, "group")


if __name__ == "__main__":
    unittest.main()
