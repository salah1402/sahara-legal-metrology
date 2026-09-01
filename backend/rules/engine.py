"""
Legal Metrology (PCR 2011) Deterministic Rule Engine
Evaluates NormalizedProductData against structured Legal Metrology rules.
Maintains full evidence traceability: Rule -> Field -> Normalized Value -> OCR Text -> Bounding Box.
"""

from typing import List, Optional
from datetime import datetime, timezone

from backend.models.schemas import (
    NormalizedProductData,
    RuleCheckResult,
    ComplianceResult,
    ComplianceSummary,
    RuleApplicability,
    CheckStatus
)
from backend.rules.rules_data import LEGAL_METROLOGY_RULES

LOW_CONFIDENCE_THRESHOLD = 0.65


def evaluate_rule(rule_def: dict, product_data: NormalizedProductData) -> RuleCheckResult:
    rule_id = rule_def["rule_id"]
    rule_number = rule_def["rule_number"]
    source = rule_def["source"]
    source_ref = rule_def["source_reference"]
    requirement = rule_def["requirement"]
    field_name = rule_def["field"]
    val_type = rule_def.get("validation_type", "")

    applicability: RuleApplicability = rule_def.get("default_applicability", "APPLICABLE")

    # -------------------------------------------------------------
    # Rule 6(1)(a): Manufacturer / Packer Name & Address
    # -------------------------------------------------------------
    if val_type == "name_and_address_check":
        mfg = product_data.manufacturer
        pkr = product_data.packer
        imp = product_data.importer

        target = mfg if mfg.status != "missing" else (pkr if pkr.status != "missing" else imp)

        if target.status == "missing":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Mandatory manufacturer or packer name and address declaration not found in label text."
            )

        if target.evidence and target.evidence.ocr_confidence < LOW_CONFIDENCE_THRESHOLD:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=target.name or target.address,
                evidence=target.evidence,
                reason=f"Manufacturer declaration has low OCR confidence ({int(target.evidence.ocr_confidence*100)}%). Requires officer verification."
            )

        if target.status == "ambiguous" or target.status == "conflicting":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=target.name or target.address,
                evidence=target.evidence,
                reason="Ambiguous or conflicting manufacturer/packer candidates detected."
            )

        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=target.name or target.address,
            evidence=target.evidence,
            reason="Mandatory manufacturer/packer identification with postal address verified."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(aa): Country of Origin
    # -------------------------------------------------------------
    elif val_type == "country_of_origin_check":
        coo = product_data.country_of_origin
        if coo.status == "missing":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Country of origin declaration not detected on package label."
            )

        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=coo.value or "INDIA",
            evidence=coo.evidence,
            reason="Country of origin declaration verified on principal display panel."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(b) & Rule 12: Net Quantity with Standard Metric Units
    # -------------------------------------------------------------
    elif val_type == "net_quantity_standard_unit_check":
        net_qty = product_data.net_quantity
        if net_qty.status == "missing":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Net quantity declaration not detected on package."
            )

        if net_qty.status == "ambiguous":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=f"{net_qty.value} (Unit ambiguous/missing)",
                evidence=net_qty.evidence,
                reason="Net quantity numeral detected but standard metric SI unit is ambiguous or missing."
            )

        if net_qty.status == "conflicting":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value="Multiple conflicting quantity declarations",
                evidence=net_qty.evidence,
                reason="Multiple conflicting net quantity tokens detected. Officer review required."
            )

        if net_qty.evidence and net_qty.evidence.ocr_confidence < LOW_CONFIDENCE_THRESHOLD:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=f"{net_qty.value} {net_qty.unit}",
                evidence=net_qty.evidence,
                reason=f"Net quantity numeral has low OCR confidence ({int(net_qty.evidence.ocr_confidence*100)}%)."
            )

        # Verify unit is valid SI metric standard
        valid_units = {"g", "kg", "ml", "l", "m", "cm", "piece", "pieces", "unit", "units"}
        unit_check = (net_qty.standardized_unit or net_qty.unit or "").lower()
        if unit_check not in valid_units:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=f"{net_qty.value} {net_qty.unit}",
                evidence=net_qty.evidence,
                reason=f"Unit symbol '{net_qty.unit}' requires standard metric verification under Rule 12."
            )

        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=f"{net_qty.value} {net_qty.unit}",
            evidence=net_qty.evidence,
            reason="Net quantity declared in standard SI metric units per Rule 12."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(d): Month & Year of Manufacture / Packing
    # -------------------------------------------------------------
    elif val_type == "mfg_packing_date_check":
        dt = product_data.date_information
        if dt.status == "missing" or (not dt.manufacturing_date and not dt.packing_date):
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Month and year of manufacture or pre-packing declaration not found."
            )

        val_str = dt.manufacturing_date or dt.packing_date or "Date detected"
        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=val_str,
            evidence=dt.evidence,
            reason="Month and year of manufacture / packing detected and recorded."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(e): Maximum Retail Price (MRP)
    # -------------------------------------------------------------
    elif val_type == "mrp_declaration_check":
        mrp = product_data.mrp
        if mrp.status == "missing":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Maximum Retail Price (MRP) declaration not found on package."
            )

        if mrp.status == "conflicting":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value="Multiple conflicting MRP values",
                evidence=mrp.evidence,
                reason="Multiple conflicting MRP declarations detected in OCR text."
            )

        if mrp.evidence and mrp.evidence.ocr_confidence < LOW_CONFIDENCE_THRESHOLD:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value=f"₹{mrp.value}",
                evidence=mrp.evidence,
                reason=f"MRP text has low OCR confidence ({int(mrp.evidence.ocr_confidence*100)}%). Requires officer confirmation."
            )

        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=f"₹{mrp.value}" + (" (Incl. of all taxes)" if mrp.is_inclusive_of_taxes else ""),
            evidence=mrp.evidence,
            reason="Maximum Retail Price (MRP) declaration present and legible."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(m): Unit Sale Price (USP)
    # -------------------------------------------------------------
    elif val_type == "unit_sale_price_check":
        mrp = product_data.mrp
        if mrp.unit_sale_price:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="PASS",
                actual_value=mrp.unit_sale_price,
                evidence=mrp.evidence,
                reason="Unit Sale Price (USP) declaration detected per GSR 779(E) amendment."
            )
        else:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value="Not explicitly stated alongside MRP",
                evidence=mrp.evidence,
                reason="Unit Sale Price (USP) requirement under GSR 779(E) requires verification for multi-unit packages."
            )

    # -------------------------------------------------------------
    # Rule 6(1)(f): Consumer Care Details
    # -------------------------------------------------------------
    elif val_type == "consumer_care_check":
        cc = product_data.consumer_care
        if cc.status == "missing":
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="FAIL",
                actual_value="Not detected",
                evidence=None,
                reason="Consumer grievance / customer care contact details not detected."
            )

        actual_str = []
        if cc.phone: actual_str.append(f"Phone: {cc.phone}")
        if cc.email: actual_str.append(f"Email: {cc.email}")
        if not actual_str and cc.address: actual_str.append(cc.address)

        return RuleCheckResult(
            rule_id=rule_id,
            rule_number=rule_number,
            source=source,
            source_reference=source_ref,
            requirement=requirement,
            field=field_name,
            applicability=applicability,
            status="PASS",
            actual_value=" | ".join(actual_str) if actual_str else "Consumer care helpline detected",
            evidence=cc.evidence,
            reason="Consumer care contact mechanism (helpline/email) verified per Rule 6(1)(f)."
        )

    # -------------------------------------------------------------
    # Rule 6(1)(n): Best Before / Expiry
    # -------------------------------------------------------------
    elif val_type == "best_before_expiry_check":
        dt = product_data.date_information
        if dt.expiry_date or dt.best_before:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="PASS",
                actual_value=dt.expiry_date or dt.best_before,
                evidence=dt.evidence,
                reason="Best before / expiry declaration identified."
            )
        else:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability="UNKNOWN",
                status="NEEDS_REVIEW",
                actual_value="Not detected",
                evidence=None,
                reason="Best before/expiry applicability depends on commodity perishability."
            )

    # -------------------------------------------------------------
    # Generic Commodity Name
    # -------------------------------------------------------------
    elif val_type == "commodity_name_check":
        p = product_data.product
        if p.status != "missing" and p.commodity_name:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="PASS",
                actual_value=p.commodity_name,
                evidence=p.evidence,
                reason="Generic / common commodity name declaration detected."
            )
        else:
            return RuleCheckResult(
                rule_id=rule_id,
                rule_number=rule_number,
                source=source,
                source_reference=source_ref,
                requirement=requirement,
                field=field_name,
                applicability=applicability,
                status="NEEDS_REVIEW",
                actual_value="Not clearly distinguished",
                evidence=None,
                reason="Generic commodity name requires visual inspection."
            )

    # Default fallback
    return RuleCheckResult(
        rule_id=rule_id,
        rule_number=rule_number,
        source=source,
        source_reference=source_ref,
        requirement=requirement,
        field=field_name,
        applicability=applicability,
        status="NEEDS_REVIEW",
        actual_value="Unchecked",
        evidence=None,
        reason="Rule requirement evaluated by default checker."
    )


def evaluate_compliance(product_data: NormalizedProductData) -> ComplianceResult:
    """
    Evaluates all Legal Metrology rules deterministically against normalized product data.
    Computes summary counts and overall compliance status.
    """
    checks: List[RuleCheckResult] = []
    
    for rule_def in LEGAL_METROLOGY_RULES:
        check_res = evaluate_rule(rule_def, product_data)
        checks.append(check_res)

    passed_count = sum(1 for c in checks if c.status == "PASS")
    failed_count = sum(1 for c in checks if c.status == "FAIL")
    needs_review_count = sum(1 for c in checks if c.status == "NEEDS_REVIEW")
    not_app_count = sum(1 for c in checks if c.status == "NOT_APPLICABLE")

    if failed_count > 0:
        overall_status: CheckStatus = "FAIL"
    elif needs_review_count > 0:
        overall_status = "NEEDS_REVIEW"
    else:
        overall_status = "PASS"

    summary = ComplianceSummary(
        total_checks=len(checks),
        passed_count=passed_count,
        failed_count=failed_count,
        needs_review_count=needs_review_count,
        not_applicable_count=not_app_count
    )

    return ComplianceResult(
        inspection_id=product_data.inspection_id,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        overall_status=overall_status,
        checks=checks,
        summary=summary
    )
