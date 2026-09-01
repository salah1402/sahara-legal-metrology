import re
import logging
from typing import List, Dict, Any, Optional

from backend.models.schemas import StructuredProductData, ExtractedField, Evidence
from backend.models.compliance import (
    ApplicabilityFacts,
    CheckStatus,
    OverallStatus,
    LegalSource,
    RuleApplicabilityDecision,
    RuleCheckResult,
    ExemptionAuditInfo,
    ComplianceSummary,
    LegalFrameworkInfo,
    ComplianceResult
)

logger = logging.getLogger("sahara_compliance_evaluator")


def is_full_package_coverage(product_data: StructuredProductData) -> bool:
    """
    Determines if sufficient package coverage (e.g. front + back, or multiple comprehensive panels)
    has been supplied to establish definitive absence rather than partial view uncertainty.
    """
    if len(product_data.images) >= 2:
        types = {img.image_type for img in product_data.images}
        if "front_panel" in types and "back_panel" in types:
            return True
        if len(types) >= 3:
            return True
    return False


def build_legal_source(source_dict: Dict[str, Any]) -> LegalSource:
    return LegalSource(
        instrument=source_dict.get("instrument", "Legal Metrology (Packaged Commodities) Rules, 2011"),
        notification=source_dict.get("notification"),
        effective_from=source_dict.get("effective_from", "2011-04-01"),
        source_url=source_dict.get("source_url"),
        source_type=source_dict.get("source_type", "official_gazette")
    )


def create_rule_26_exemption_info(applicability: ApplicabilityFacts, evidence: List[Evidence]) -> ExemptionAuditInfo:
    clause = applicability.rule_26_clause or "26"
    return ExemptionAuditInfo(
        exemption_rule="PCR-2011-R26",
        exemption_clause=clause,
        reason=applicability.exemption_reason or f"Exempt under Rule {clause} of Legal Metrology (Packaged Commodities) Rules, 2011.",
        factual_conditions_checked=applicability.exemption_conditions or [f"Statutory requirements under Clause {clause} satisfied"],
        evidence=evidence
    )


def evaluate_compliance(
    product_data: StructuredProductData,
    applicability: ApplicabilityFacts,
    active_rules: List[Dict[str, Any]],
    inspection_date: str
) -> ComplianceResult:
    """
    Deterministic Legal Metrology compliance evaluation engine.
    Executes versioned statutory checks against StructuredProductData and ApplicabilityFacts.
    Strictly distinguishes between PASS, FAIL, NEEDS_REVIEW, NOT_APPLICABLE, and EXEMPT.
    """
    full_coverage = is_full_package_coverage(product_data)
    prod = product_data.product
    checks: List[RuleCheckResult] = []

    passed_count = 0
    failed_count = 0
    needs_review_count = 0
    not_applicable_count = 0
    exempt_count = 0

    for rule in active_rules:
        rule_id = rule.get("rule_id", "UNKNOWN")
        rule_number = rule.get("rule_number", "")
        title = rule.get("title", "")
        evaluator_info = rule.get("evaluator", {})
        handler_name = evaluator_info.get("handler", "")
        source = build_legal_source(rule.get("source", {}))

        # Default values
        status: CheckStatus = "NEEDS_REVIEW"
        app_decision = RuleApplicabilityDecision(status="APPLICABLE", reason="Rule is applicable.")
        observed_val: Optional[str] = None
        required_val: Optional[str] = None
        reason: str = ""
        evidence_list: List[Evidence] = []
        exemption_info: Optional[ExemptionAuditInfo] = None

        # =========================================================================
        # 1. Rule 6(1)(a): Manufacturer / Packer / Importer Name & Address
        # =========================================================================
        if handler_name == "evaluate_manufacturer_packer_importer":
            required_val = "Name and complete address of manufacturer, packer, or importer."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt from Chapter II declarations under statutory Rule {applicability.rule_26_clause or '26'}."
                evidence_list = prod.net_quantity.evidence
                exemption_info = create_rule_26_exemption_info(applicability, evidence_list)
            elif prod.manufacturer.status == "extracted" and prod.manufacturer.value:
                status = "PASS"
                observed_val = prod.manufacturer.value
                reason = "Manufacturer name and address clearly declared on package."
                evidence_list = prod.manufacturer.evidence or prod.manufacturer_address.evidence
            elif prod.packer.status == "extracted" and prod.packer.value:
                status = "PASS"
                observed_val = prod.packer.value
                reason = "Packer name and address declared on package."
                evidence_list = prod.packer.evidence or prod.packer_address.evidence
            elif prod.importer.status == "extracted" and prod.importer.value:
                status = "PASS"
                observed_val = prod.importer.value
                reason = "Importer name and address declared on package."
                evidence_list = prod.importer.evidence or prod.importer_address.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Required manufacturer, packer, or importer name and address were not found on the package after full coverage inspection."
            else:
                status = "NEEDS_REVIEW"
                reason = "Manufacturer/packer declaration not observed in supplied image(s). Other package panels must be inspected."

        # =========================================================================
        # 2. Rule 6(1)(aa): Country of Origin (Imported Commodities)
        # =========================================================================
        elif handler_name == "evaluate_country_of_origin":
            required_val = "Country of origin / manufacture for imported commodities."
            if not applicability.is_imported:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Product is of domestic Indian manufacture.")
                reason = "Domestic product — Country of origin declaration is mandatory only for imported products under Rule 6(1)(aa)."
                if prod.country_of_origin.status == "extracted" and prod.country_of_origin.value:
                    observed_val = prod.country_of_origin.value
                    evidence_list = prod.country_of_origin.evidence
            else:
                if prod.country_of_origin.status == "extracted" and prod.country_of_origin.value:
                    status = "PASS"
                    observed_val = prod.country_of_origin.value
                    reason = f"Country of origin declared as '{prod.country_of_origin.value}'."
                    evidence_list = prod.country_of_origin.evidence
                elif full_coverage:
                    status = "FAIL"
                    reason = "Imported commodity does not declare country of origin on package."
                else:
                    status = "NEEDS_REVIEW"
                    reason = "Imported commodity without country of origin observed on supplied image(s)."

        # =========================================================================
        # 3. Rule 6(1)(b): Common or Generic Commodity Name
        # =========================================================================
        elif handler_name == "evaluate_commodity_name":
            required_val = "Common or generic name of commodity."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif prod.commodity_name.status == "extracted" and prod.commodity_name.value:
                status = "PASS"
                observed_val = prod.commodity_name.value
                reason = f"Common / generic commodity name declared as '{prod.commodity_name.value}'."
                evidence_list = prod.commodity_name.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Common or generic commodity name was not found on package."
            else:
                status = "NEEDS_REVIEW"
                reason = "Generic commodity name not observed in supplied image(s)."

        # =========================================================================
        # 4. Rule 6(1)(c): Net Quantity in Standard Metric Units
        # =========================================================================
        elif handler_name == "evaluate_net_quantity":
            required_val = "Net quantity in standard metric units (g, kg, mL, L, units/N)."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt from mandatory net quantity declarations under statutory Rule {applicability.rule_26_clause or '26'}."
                if prod.net_quantity.status == "extracted":
                    observed_val = f"{prod.net_quantity.value} {prod.net_quantity.unit or ''}".strip()
                    evidence_list = prod.net_quantity.evidence
                exemption_info = create_rule_26_exemption_info(applicability, evidence_list)
            elif prod.net_quantity.status == "extracted" and prod.net_quantity.value is not None:
                valid_units = {"g", "kg", "mg", "ml", "l", "cm", "m", "mm", "units", "pieces", "n"}
                u = (prod.net_quantity.unit or "").lower()
                if u in valid_units:
                    status = "PASS"
                    observed_val = f"{prod.net_quantity.value} {prod.net_quantity.unit}"
                    reason = f"Net quantity declared in standard metric units: {observed_val}."
                    evidence_list = prod.net_quantity.evidence
                else:
                    status = "FAIL"
                    observed_val = f"{prod.net_quantity.value} {prod.net_quantity.unit or 'UNKNOWN'}"
                    reason = f"Net quantity declared with non-standard unit '{prod.net_quantity.unit}'."
                    evidence_list = prod.net_quantity.evidence
            elif prod.net_quantity.status == "ambiguous":
                status = "NEEDS_REVIEW"
                observed_val = str(prod.net_quantity.value)
                reason = "Net quantity numeral detected without clear, unambiguous standard metric unit."
                evidence_list = prod.net_quantity.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Net quantity declaration was not found on the package."
            else:
                status = "NEEDS_REVIEW"
                reason = "Net quantity not observed in supplied image(s)."

        # =========================================================================
        # 5. Rule 6(1)(d): Month & Year of Manufacture / Packing / Import
        # =========================================================================
        elif handler_name == "evaluate_manufacturing_or_packing_date":
            required_val = "Month and year of manufacture, packing, or import (e.g. MM/YYYY)."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif prod.manufacturing_date.status == "extracted" and prod.manufacturing_date.value:
                status = "PASS"
                observed_val = prod.manufacturing_date.value
                reason = f"Manufacturing/packing date declared: {prod.manufacturing_date.value}."
                evidence_list = prod.manufacturing_date.evidence
            elif prod.packing_date.status == "extracted" and prod.packing_date.value:
                status = "PASS"
                observed_val = prod.packing_date.value
                reason = f"Packing date declared: {prod.packing_date.value}."
                evidence_list = prod.packing_date.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Month and year of manufacture or packing was not found on package."
            else:
                status = "NEEDS_REVIEW"
                reason = "Manufacturing / packing date not observed in supplied image(s)."

        # =========================================================================
        # 6. Rule 6(1)(e): Maximum Retail Price (MRP inclusive of all taxes)
        # =========================================================================
        elif handler_name == "evaluate_mrp":
            required_val = "Maximum Retail Price in Indian Rupees inclusive of all taxes."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif not applicability.intended_for_retail_sale:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Non-retail or wholesale package.")
                reason = "Non-retail package — Chapter II MRP provisions apply to retail sales."
            elif prod.mrp.status == "extracted" and prod.mrp.value is not None:
                status = "PASS"
                observed_val = f"₹ {prod.mrp.value:.2f} (Incl. of all taxes)"
                reason = f"MRP clearly declared: ₹ {prod.mrp.value:.2f} inclusive of all taxes."
                evidence_list = prod.mrp.evidence
            elif prod.mrp.status == "conflicting":
                status = "FAIL"
                observed_val = f"Conflicting values: {[c.value for c in prod.mrp.candidates or []]}"
                reason = "Multiple conflicting MRP declarations detected on package (dual pricing violation under Rule 6(1)(e))."
                evidence_list = prod.mrp.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Maximum Retail Price (MRP) declaration was not found on retail package."
            else:
                status = "NEEDS_REVIEW"
                reason = "MRP declaration not observed in supplied image(s)."

        # =========================================================================
        # 7. Rule 6(1)(f): Consumer Care Helpline Details
        # =========================================================================
        elif handler_name == "evaluate_consumer_care":
            required_val = "Consumer grievance helpline (Name, Telephone, Email, or Address)."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif not applicability.intended_for_retail_sale:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Non-retail package.")
                reason = "Non-retail package — Consumer care mandate applies to retail commodities."
            elif (prod.consumer_care_phone.status == "extracted" and prod.consumer_care_phone.value) or \
                 (prod.consumer_care_email.status == "extracted" and prod.consumer_care_email.value) or \
                 (prod.consumer_care.status == "extracted" and prod.consumer_care.value):
                status = "PASS"
                parts = []
                if prod.consumer_care_phone.value: parts.append(f"Tel: {prod.consumer_care_phone.value}")
                if prod.consumer_care_email.value: parts.append(f"Email: {prod.consumer_care_email.value}")
                if prod.consumer_care.value: parts.append(prod.consumer_care.value)
                observed_val = " | ".join(parts)
                reason = f"Consumer grievance contact details declared: {observed_val}."
                evidence_list = prod.consumer_care_phone.evidence + prod.consumer_care_email.evidence + prod.consumer_care.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Consumer grievance helpline/contact details were not found on retail package."
            else:
                status = "NEEDS_REVIEW"
                reason = "Consumer care contact information not observed in supplied image(s)."

        # =========================================================================
        # 8. Rule 6(1)(m): Unit Sale Price (USP)
        # =========================================================================
        elif handler_name == "evaluate_unit_sale_price":
            required_val = "Unit Sale Price (USP) in Rupees per standard unit according to Rule 6(11) thresholds."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif not applicability.intended_for_retail_sale:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Exempt or non-retail package.")
                reason = "USP mandate applies only to retail prepackaged commodities."
            else:
                # Check for USP in other_detected_information
                usp_item = next((item for item in product_data.other_detected_information if item.category == "pricing" and "unit sale price" in item.label.lower()), None)
                if usp_item:
                    # Check threshold logic
                    qty_val = prod.net_quantity.value
                    qty_unit = (prod.net_quantity.unit or "").lower()
                    status = "PASS"
                    observed_val = str(usp_item.value)
                    reason = f"Unit Sale Price declared as '{usp_item.value}'."
                    evidence_list = usp_item.evidence

                    usp_clean = re.sub(r'\s+', '', str(usp_item.value).lower())
                    if qty_val is not None and qty_unit in ["g", "gm", "gms"]:
                        if qty_val < 1000 and ("/kg" in usp_clean or "perkg" in usp_clean) and ("/g" not in usp_clean and "perg" not in usp_clean):
                            status = "FAIL"
                            reason = f"USP declared per kg for package under 1 kg ({qty_val} g). Rule 6(11) requires USP per gram for packages < 1 kg."
                    elif qty_val is not None and qty_unit in ["ml", "mls", "millilitre"]:
                        if qty_val < 1000 and ("/l" in usp_clean or "perl" in usp_clean or "/litre" in usp_clean) and ("/ml" not in usp_clean and "perml" not in usp_clean):
                            status = "FAIL"
                            reason = f"USP declared per litre for package under 1 L ({qty_val} mL). Rule 6(11) requires USP per mL for packages < 1 L."
                elif prod.mrp.value is not None and prod.net_quantity.value is not None:
                    qty_val = prod.net_quantity.value
                    qty_unit = (prod.net_quantity.unit or "").lower()
                    mrp_val = prod.mrp.value

                    expected_usp_str = ""
                    if qty_unit in ["g", "gm", "gms"]:
                        if qty_val < 1000:
                            expected_usp_str = f"₹ {mrp_val / qty_val:.2f} / g"
                        else:
                            expected_usp_str = f"₹ {mrp_val / (qty_val / 1000.0):.2f} / kg"
                    elif qty_unit in ["ml", "mls"]:
                        if qty_val < 1000:
                            expected_usp_str = f"₹ {mrp_val / qty_val:.2f} / mL"
                        else:
                            expected_usp_str = f"₹ {mrp_val / (qty_val / 1000.0):.2f} / L"

                    if full_coverage:
                        status = "FAIL"
                        observed_val = "Not declared"
                        required_val = expected_usp_str or "USP per standard metric unit"
                        reason = f"Unit Sale Price (USP) declaration missing. Expected: {expected_usp_str}."
                    else:
                        status = "NEEDS_REVIEW"
                        observed_val = "Not observed"
                        required_val = expected_usp_str or "USP per standard metric unit"
                        reason = f"Unit Sale Price not observed in supplied image. Calculated reference: {expected_usp_str}."
                elif full_coverage:
                    status = "FAIL"
                    reason = "Unit Sale Price (USP) was not found on package."
                else:
                    status = "NEEDS_REVIEW"
                    reason = "Unit Sale Price (USP) not observed in supplied image(s)."

        # =========================================================================
        # 9. Rule 6(1) Proviso: Best Before / Expiry for Perishable Commodities
        # =========================================================================
        elif handler_name == "evaluate_best_before_or_expiry":
            required_val = "Best before or use by date for perishable commodities."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif applicability.commodity_type not in ["food", "beverage", "dairy", "edible_oil", "perishable"]:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason=f"Commodity type '{applicability.commodity_type}' is non-perishable.")
                reason = f"Non-perishable commodity ({applicability.commodity_type}) — Best before date is not mandatory under Rule 6(1)."
            elif prod.best_before.status == "extracted" and prod.best_before.value:
                status = "PASS"
                observed_val = prod.best_before.value
                reason = f"Best before date declared: {prod.best_before.value}."
                evidence_list = prod.best_before.evidence
            elif prod.expiry_date.status == "extracted" and prod.expiry_date.value:
                status = "PASS"
                observed_val = prod.expiry_date.value
                reason = f"Expiry date declared: {prod.expiry_date.value}."
                evidence_list = prod.expiry_date.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Perishable food commodity does not declare best before or expiry date."
            else:
                status = "NEEDS_REVIEW"
                reason = "Best before date not observed in supplied image(s)."

        # =========================================================================
        # 10. Rule 4: Group / Combination Packages
        # =========================================================================
        elif handler_name == "evaluate_group_combination_packages":
            required_val = "Number of items, net quantity of components, and total MRP on group packaging."
            if not applicability.is_group_package and not applicability.is_combination_package and not applicability.is_multi_piece_package:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Package is an individual retail commodity.")
                reason = "Single unit commodity — Rule 4 group packaging provisions do not apply."
            elif prod.number_of_items.value and prod.number_of_items.value > 1 and prod.net_quantity.status == "extracted":
                status = "PASS"
                observed_val = f"{prod.number_of_items.value} items, Net Qty: {prod.net_quantity.value} {prod.net_quantity.unit or ''}".strip()
                reason = f"Group packaging declares item count ({prod.number_of_items.value}) and total net quantity."
                evidence_list = prod.number_of_items.evidence + prod.net_quantity.evidence
            else:
                status = "NEEDS_REVIEW"
                reason = "Group package component details or individual package declarations require physical verification."

        # =========================================================================
        # 11. Rule 7 & 8: Principal Display Panel & Minimum Character Height
        # =========================================================================
        elif handler_name == "evaluate_font_size_and_pdp":
            required_val = "Minimum character height in accordance with Rule 7 Table."
            status = "NEEDS_REVIEW"
            observed_val = "Pixel bounding boxes available without physical mm calibration"
            reason = "Physical character height cannot be verified from the supplied image without scale/calibration."
            evidence_list = prod.net_quantity.evidence

        # =========================================================================
        # 12. Rule 9: Manner of Declarations & Legibility
        # =========================================================================
        elif handler_name == "evaluate_manner_of_declaration":
            required_val = "Declarations legible, prominent, and in distinct contrast."
            all_ev = prod.mrp.evidence + prod.net_quantity.evidence + prod.commodity_name.evidence
            low_conf = [ev for ev in all_ev if ev.ocr_confidence is not None and ev.ocr_confidence < 0.50]
            if low_conf:
                status = "NEEDS_REVIEW"
                observed_val = f"Low OCR confidence ({low_conf[0].ocr_confidence:.2f}) on '{low_conf[0].source_text}'"
                reason = "Visual legibility / contrast cannot be conclusively established due to low optical clarity."
                evidence_list = low_conf
            elif all_ev:
                status = "PASS"
                observed_val = "High optical clarity and distinct contrast"
                reason = "Mandatory declarations are legible and prominent."
                evidence_list = all_ev[:3]
            else:
                status = "NEEDS_REVIEW"
                reason = "Legibility requires physical package review."

        # =========================================================================
        # 13. Rule 10: Complete Address Declaration
        # =========================================================================
        elif handler_name == "evaluate_complete_address":
            required_val = "Complete postal address of manufacturer, packer, or importer."
            addr_val = prod.manufacturer_address.value or prod.packer_address.value or prod.importer_address.value
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            elif addr_val:
                status = "PASS"
                observed_val = addr_val
                reason = f"Complete address declared: '{addr_val}'."
                evidence_list = prod.manufacturer_address.evidence or prod.packer_address.evidence or prod.importer_address.evidence
            elif full_coverage:
                status = "FAIL"
                reason = "Complete address declaration was not found on package."
            else:
                status = "NEEDS_REVIEW"
                reason = "Address declaration not observed in supplied image(s)."

        # =========================================================================
        # 14. Rule 12 & 13: Standard Metric Units
        # =========================================================================
        elif handler_name == "evaluate_standard_units":
            required_val = "Standard metric units of weight, measure or count (Rule 12)."
            if prod.net_quantity.status == "extracted" and prod.net_quantity.unit:
                u = prod.net_quantity.unit.lower()
                if u in ["g", "kg", "mg", "ml", "l", "cm", "m", "mm", "units", "pieces", "n"]:
                    status = "PASS"
                    observed_val = prod.net_quantity.unit
                    reason = f"Standard metric unit '{prod.net_quantity.unit}' conforms with Rule 12 & 13."
                    evidence_list = prod.net_quantity.evidence
                else:
                    status = "FAIL"
                    observed_val = prod.net_quantity.unit
                    reason = f"Non-standard metric unit '{prod.net_quantity.unit}' violates Rule 12."
                    evidence_list = prod.net_quantity.evidence
            elif applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Exempt under Rule 26.")
                reason = f"Exempt under Rule {applicability.rule_26_clause or '26'} statutory exemption."
                exemption_info = create_rule_26_exemption_info(applicability, prod.net_quantity.evidence)
            else:
                status = "NEEDS_REVIEW"
                reason = "Standard unit compliance requires net quantity observation."

        # =========================================================================
        # 15. Rule 18: Price Revision Restrictions
        # =========================================================================
        elif handler_name == "evaluate_price_revision":
            required_val = "No smudging, alteration, or overcharging beyond declared MRP."
            if not applicability.is_price_revision_scenario:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Standard inspection scenario (no price alteration/re-stickering under review).")
                reason = "Rule 18 applies conditionally when price alterations or re-stickering are under inspection."
            elif prod.mrp.status == "conflicting":
                status = "FAIL"
                observed_val = "Conflicting/altered price declarations"
                reason = "Price alterations / conflicting stickering detected in violation of Rule 18."
                evidence_list = prod.mrp.evidence
            else:
                status = "PASS"
                observed_val = f"Single declared MRP: ₹ {prod.mrp.value:.2f}" if prod.mrp.value else "Clean declaration"
                reason = "No unauthorized price smudging or alteration observed."
                evidence_list = prod.mrp.evidence

        # =========================================================================
        # 16. Rule 24: Wholesale Packages
        # =========================================================================
        elif handler_name == "evaluate_wholesale_package":
            required_val = "Wholesale package declarations under Chapter III."
            if not applicability.is_wholesale_package:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Commodity is a retail package.")
                reason = "Retail package — Wholesale package provisions under Chapter III do not apply."
            elif prod.manufacturer.value and prod.commodity_name.value and prod.net_quantity.value:
                status = "PASS"
                observed_val = f"{prod.commodity_name.value} | {prod.manufacturer.value} | {prod.net_quantity.value} {prod.net_quantity.unit or ''}"
                reason = "Wholesale package contains mandatory identity, manufacturer, and net quantity declarations."
                evidence_list = prod.manufacturer.evidence + prod.commodity_name.evidence + prod.net_quantity.evidence
            else:
                status = "NEEDS_REVIEW"
                reason = "Wholesale package declarations require verification of outer bulk packaging."

        # =========================================================================
        # 17. Rule 25: Export Packages
        # =========================================================================
        elif handler_name == "evaluate_export_package":
            required_val = "Export package marking ('FOR EXPORT ONLY')."
            if not applicability.is_export_package:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Commodity is intended for domestic Indian market.")
                reason = "Domestic retail package — Export exemptions under Rule 25 do not apply."
            else:
                status = "PASS"
                observed_val = "Export packaging declaration"
                reason = "Package is marked for export and exempt from domestic retail Chapter II requirements."

        # =========================================================================
        # 18. Rule 26: General Statutory Exemptions
        # =========================================================================
        elif handler_name == "evaluate_rule_26_exemptions":
            required_val = "Statutory exemption criteria under Rule 26 clauses (a), (b), (c), (d), (e), (f)."
            if applicability.is_exempt_under_rule_26:
                status = "EXEMPT"
                clause = applicability.rule_26_clause or "26"
                app_decision = RuleApplicabilityDecision(status="EXEMPT", reason=applicability.exemption_reason or "Statutory exemption verified.")
                observed_val = f"Exempt under Clause {clause} ({applicability.exemption_reason})"
                reason = f"Statutory exemption verified under Rule {clause}: {applicability.exemption_reason}"
                evidence_list = prod.net_quantity.evidence
                exemption_info = create_rule_26_exemption_info(applicability, evidence_list)
            elif applicability.is_garment_or_hosiery:
                status = "NEEDS_REVIEW"
                observed_val = "Garment / Hosiery commodity"
                reason = "Garments sold in loose/open form are exempt under Rule 26(e); physical/inspector review needed to establish if item was sold in open/loose form."
            else:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Standard retail commodity not qualifying for Rule 26 exemptions.")
                reason = "Standard packaged commodity subject to general Chapter II declarations (no Rule 26 exemption applies)."

        # =========================================================================
        # 19. Electronic Products QR Code Provisions (2023 Amendment)
        # =========================================================================
        elif handler_name == "evaluate_electronic_qr_provisions":
            required_val = "Basic declarations on package (MRP, Name, Consumer Care, Origin) with QR code for detailed specifications."
            if not applicability.is_electronic_product:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Commodity is not an electronic product.")
                reason = "Electronic products QR code provisions (2023 Amendment) do not apply to general non-electronic goods."
            else:
                has_basic = bool(prod.mrp.value and prod.commodity_name.value and (prod.consumer_care_phone.value or prod.consumer_care_email.value))
                if has_basic:
                    status = "PASS"
                    observed_val = f"MRP: ₹ {prod.mrp.value:.2f} | Commodity: {prod.commodity_name.value}"
                    reason = "Electronic product contains basic mandatory declarations on package (MRP, commodity name, consumer care) as permitted under 2023 QR amendment."
                    evidence_list = prod.mrp.evidence + prod.commodity_name.evidence
                else:
                    status = "NEEDS_REVIEW"
                    reason = "Electronic product requires verification of on-package basic declarations and QR code scannability."

        # =========================================================================
        # 20. Medical Devices 2025 Amendment
        # =========================================================================
        elif handler_name == "evaluate_medical_device_exclusion":
            required_val = "Medical Devices Rules, 2017 statutory requirements."
            if not applicability.is_medical_device:
                status = "NOT_APPLICABLE"
                app_decision = RuleApplicabilityDecision(status="NOT_APPLICABLE", reason="Commodity is not a medical device.")
                reason = "General packaged commodity — Medical Devices Rules override does not apply."
            else:
                status = "PASS"
                app_decision = RuleApplicabilityDecision(status="APPLICABLE", reason="Medical device identified.")
                observed_val = f"Medical device ({prod.commodity_name.value or 'Device'})"
                reason = "LMPC medical-device exclusion/override detected — Medical Devices Rules, 2017 apply in lieu of general LMPC typography/declarations."
                evidence_list = prod.commodity_name.evidence

        # =========================================================================
        # Default / Fallback
        # =========================================================================
        else:
            status = "NEEDS_REVIEW"
            reason = f"Evaluation handler '{handler_name}' requires manual inspection review."

        # Update Summary counts
        if status == "PASS":
            passed_count += 1
        elif status == "FAIL":
            failed_count += 1
        elif status == "NEEDS_REVIEW":
            needs_review_count += 1
        elif status == "NOT_APPLICABLE":
            not_applicable_count += 1
        elif status == "EXEMPT":
            exempt_count += 1

        checks.append(RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            title=title,
            status=status,
            applicability=app_decision,
            observed_value=observed_val,
            required_value=required_val,
            reason=reason,
            evidence=evidence_list,
            legal_source=source,
            exemption=exemption_info
        ))

    # =========================================================================
    # Overall Status Aggregation
    # If any applicable rule = FAIL -> NON_COMPLIANT
    # Else if any applicable rule = NEEDS_REVIEW -> NEEDS_REVIEW
    # Else (all applicable rules are PASS, NOT_APPLICABLE, or EXEMPT) -> COMPLIANT
    # =========================================================================
    overall_status: OverallStatus = "COMPLIANT"
    if failed_count > 0:
        overall_status = "NON_COMPLIANT"
    elif needs_review_count > 0:
        overall_status = "NEEDS_REVIEW"
    else:
        overall_status = "COMPLIANT"

    summary = ComplianceSummary(
        total_checks=len(checks),
        passed=passed_count,
        failed=failed_count,
        needs_review=needs_review_count,
        not_applicable=not_applicable_count,
        exempt=exempt_count
    )

    framework_info = LegalFrameworkInfo(
        name="Legal Metrology (Packaged Commodities) Rules, 2011",
        registry_version="PCR-2011-CURRENT",
        effective_as_of=inspection_date.split("T")[0] if "T" in inspection_date else inspection_date
    )

    return ComplianceResult(
        schema_version="1.0",
        inspection_id=product_data.inspection_id,
        inspection_date=inspection_date,
        overall_status=overall_status,
        legal_framework=framework_info,
        applicability=applicability,
        summary=summary,
        checks=checks,
        evaluator_version="2.1.0"
    )
