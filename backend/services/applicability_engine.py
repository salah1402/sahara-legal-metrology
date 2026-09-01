import re
import logging
from typing import Optional, Dict, Any, List

from backend.models.schemas import StructuredProductData
from backend.models.compliance import ApplicabilityFacts

logger = logging.getLogger("sahara_applicability")


def derive_applicability_facts(
    product_data: StructuredProductData,
    inspection_hints: Optional[Dict[str, Any]] = None
) -> ApplicabilityFacts:
    """
    Deterministic fact derivation for Legal Metrology applicability.
    Derives facts strictly from verified observations without hallucination.
    NEVER assumes a Rule 26 exemption merely because a product is food or biscuits.
    """
    facts = ApplicabilityFacts()
    prod = product_data.product

    # Collect all available text representations for classification
    corpus_parts = []
    if prod.commodity_name.value:
        corpus_parts.append(str(prod.commodity_name.value).lower())
    if prod.manufacturer.value:
        corpus_parts.append(str(prod.manufacturer.value).lower())
    if prod.importer.value:
        corpus_parts.append(str(prod.importer.value).lower())
    for item in product_data.other_detected_information:
        corpus_parts.append(f"{item.label} {item.value}".lower())

    corpus = " ".join(corpus_parts)

    # 1. Imported Product Check (Rule 6(1)(aa))
    if prod.importer.status == "extracted" and prod.importer.value:
        facts.is_imported = True
    elif prod.country_of_origin.status == "extracted" and prod.country_of_origin.value:
        coo_lower = str(prod.country_of_origin.value).lower()
        if "india" not in coo_lower and "ind" != coo_lower:
            facts.is_imported = True

    # 2. Medical Device Classification (2025 Amendment / Medical Devices Rules 2017)
    med_keywords = [
        "medical device", "surgical", "catheter", "syringe", "diagnostic",
        "thermometer", "oximeter", "blood pressure monitor", "bp monitor",
        "stent", "glucometer", "lancet", "bandage", "cannula", "iv set", "iv tube"
    ]
    if any(k in corpus for k in med_keywords):
        facts.is_medical_device = True
        facts.commodity_type = "medical_device"

    # 3. Electronic Product Classification (2023 QR Provisions)
    elec_keywords = [
        "smartphone", "mobile phone", "laptop", "tablet", "charger",
        "power bank", "bluetooth", "earphone", "headphone", "smartwatch",
        "led bulb", "television", "electronic product", "adapter", "usb cable"
    ]
    if any(k in corpus for k in elec_keywords) and not facts.is_medical_device:
        facts.is_electronic_product = True
        facts.commodity_type = "electronics"

    # 4. Garments and Hosiery (Rule 26(e) conditional)
    garment_keywords = [
        "shirt", "t-shirt", "tshirt", "trouser", "jeans", "socks",
        "vest", "brief", "hosiery", "undergarment", "garment", "fabric", "kurta"
    ]
    if any(k in corpus for k in garment_keywords) and not facts.is_medical_device and not facts.is_electronic_product:
        facts.is_garment_or_hosiery = True
        facts.commodity_type = "garment"

    # 5. Food / Beverage / Perishable Commodity
    food_keywords = [
        "biscuit", "cookie", "cookies", "milk", "tea", "coffee", "juice",
        "atta", "flour", "rice", "salt", "sugar", "oil", "ghee", "butter",
        "chips", "snack", "bread", "chocolate", "confectionery", "spices", "masala", "food"
    ]
    if any(k in corpus for k in food_keywords) and facts.commodity_type == "general":
        facts.commodity_type = "food"

    # 6. Group / Combination / Multi-piece Packages (Rule 4)
    if prod.number_of_items.value and prod.number_of_items.value > 1:
        facts.is_group_package = True
        facts.package_category = "group"
    elif any(k in corpus for k in ["combo pack", "group package", "twin pack", "buy 1 get 1", "multi-pack", "multipack"]):
        facts.is_group_package = True
        facts.package_category = "group"

    # 7. Wholesale / Export Packages (Rule 24 & Rule 25)
    if any(k in corpus for k in ["wholesale package", "for wholesale", "not for retail sale", "industrial consumer"]):
        facts.is_wholesale_package = True
        facts.package_category = "wholesale"
        facts.intended_for_retail_sale = False
    elif any(k in corpus for k in ["for export only", "export pack", "for export"]):
        facts.is_export_package = True
        facts.package_category = "export"
        facts.intended_for_retail_sale = False

    # 8. Fast-Food Restaurant Packed (Rule 26(b))
    restaurant_keywords = [
        "packed by restaurant", "restaurant pack", "hotel pack", "fast food parcel",
        "freshly packed by caterer", "takeaway from restaurant"
    ]
    if any(k in corpus for k in restaurant_keywords):
        facts.is_fast_food_restaurant_packed = True
        facts.is_exempt_under_rule_26 = True
        facts.rule_26_clause = "26(b)"
        facts.exemption_reason = "Fast food item packed by restaurant/hotel (Rule 26(b) Statutory Exemption)."
        facts.exemption_conditions = [
            "Commodity is fast food prepared for consumption",
            "Packed by restaurant, hotel, or caterer",
            "Not a factory pre-packed shelf commodity"
        ]

    # 9. Institutional / Industrial Consumer Exemption (Rule 26(c))
    if any(k in corpus for k in ["for institutional consumer only", "for industrial use only", "industrial consumer"]):
        facts.is_institutional_or_industrial = True
        facts.is_exempt_under_rule_26 = True
        facts.rule_26_clause = "26(c)"
        facts.exemption_reason = "Commodity packaged exclusively for institutional/industrial consumer (Rule 26(c) Exemption)."
        facts.exemption_conditions = [
            "Packaged for institutional/industrial consumer",
            "Not for general retail sale"
        ]

    # 10. Rule 26(a) Small Package Exemption (<= 10g or <= 10mL)
    # Applied ONLY if verified package net quantity <= 10.0 (and not tobacco/pan masala)
    if not facts.is_exempt_under_rule_26 and prod.net_quantity.status == "extracted" and prod.net_quantity.value is not None:
        qty_val = prod.net_quantity.value
        qty_unit = (prod.net_quantity.unit or "").lower()
        if (qty_unit in ["g", "gm", "gms", "mg"] and qty_val <= 10.0) or \
           (qty_unit in ["ml", "mls", "millilitre"] and qty_val <= 10.0):
            # Proviso check: tobacco and pan masala are not exempt under Rule 26(a)
            if not any(k in corpus for k in ["tobacco", "bidi", "cigarette", "gutka", "pan masala", "zarda"]):
                facts.is_exempt_under_rule_26 = True
                facts.rule_26_clause = "26(a)"
                facts.package_category = "small_package"
                facts.exemption_reason = f"Net quantity {qty_val} {prod.net_quantity.unit} is <= 10 g / 10 mL (Rule 26(a) Statutory Exemption)."
                facts.exemption_conditions = [
                    f"Declared net quantity {qty_val} {prod.net_quantity.unit} <= 10 g / 10 mL",
                    "Commodity is not tobacco or pan masala",
                    "Packaged in small package format"
                ]

    # 11. Apply explicit inspector hints
    if inspection_hints:
        if inspection_hints.get("is_wholesale"):
            facts.is_wholesale_package = True
            facts.package_category = "wholesale"
            facts.intended_for_retail_sale = False
        if inspection_hints.get("is_export"):
            facts.is_export_package = True
            facts.package_category = "export"
            facts.intended_for_retail_sale = False
        if inspection_hints.get("is_price_revision"):
            facts.is_price_revision_scenario = True
        if inspection_hints.get("is_restaurant_packed"):
            facts.is_fast_food_restaurant_packed = True
            facts.is_exempt_under_rule_26 = True
            facts.rule_26_clause = "26(b)"
            facts.exemption_reason = "Fast food item packed by restaurant/hotel (Rule 26(b) Statutory Exemption)."
            facts.exemption_conditions = ["Packed by restaurant/hotel for fast-food consumption"]
        if inspection_hints.get("is_garment_loose") and facts.is_garment_or_hosiery:
            facts.is_exempt_under_rule_26 = True
            facts.rule_26_clause = "26(e)"
            facts.exemption_reason = "Garment/hosiery sold in loose/open form (Rule 26(e) Statutory Exemption)."
            facts.exemption_conditions = ["Garment/hosiery commodity", "Sold in loose or open form"]

    return facts
