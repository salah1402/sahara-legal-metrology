import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from backend.models.schemas import StructuredProductData
from backend.models.compliance import ComplianceResult
from backend.services.applicability_engine import derive_applicability_facts
from backend.services.rule_registry import get_active_rules
from backend.services.compliance_evaluator import evaluate_compliance

logger = logging.getLogger("metracheck_compliance_service")

BASE_DIR = Path(__file__).resolve().parent.parent
INSPECTIONS_DIR = BASE_DIR / "inspections"


def run_compliance_evaluation(
    inspection_id: str,
    product_data: Optional[StructuredProductData] = None,
    inspection_date: Optional[str] = None,
    inspection_hints: Optional[Dict[str, Any]] = None
) -> ComplianceResult:
    """
    Main compliance evaluation coordinator:
    1. Loads product_data.json if not provided.
    2. Derives applicability facts.
    3. Selects active versioned rules for the inspection date.
    4. Evaluates compliance deterministically.
    5. Saves compliance_result.json to inspection disk.
    6. Updates metadata.json inspection status.
    """
    insp_dir = INSPECTIONS_DIR / inspection_id
    if not insp_dir.exists():
        raise FileNotFoundError(f"Inspection directory {insp_dir} not found.")

    if product_data is None:
        norm_file = insp_dir / "normalized" / "product_data.json"
        if not norm_file.exists():
            raise FileNotFoundError(f"Normalized product data {norm_file} not found for inspection {inspection_id}.")
        with open(norm_file, "r", encoding="utf-8") as f:
            data_dict = json.load(f)
            product_data = StructuredProductData.model_validate(data_dict)

    # Resolve inspection date (defaults to metadata created_at or current UTC time)
    if not inspection_date:
        meta_file = insp_dir / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    inspection_date = meta.get("created_at")
            except Exception:
                pass
    if not inspection_date:
        inspection_date = datetime.now(timezone.utc).isoformat()

    # 1. Derive applicability
    applicability = derive_applicability_facts(product_data, inspection_hints)

    # 2. Filter active rules
    active_rules = get_active_rules(inspection_date)
    logger.info(f"Evaluating {len(active_rules)} active rules for inspection {inspection_id} as of {inspection_date}...")

    # 3. Deterministic evaluation
    compliance_result = evaluate_compliance(product_data, applicability, active_rules, inspection_date)

    # 4. Save to compliance/compliance_result.json
    comp_folder = insp_dir / "compliance"
    comp_folder.mkdir(parents=True, exist_ok=True)

    result_file = comp_folder / "compliance_result.json"
    result_dict = compliance_result.model_dump()
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    # Also write legacy result.json alias for backward compatibility
    with open(comp_folder / "result.json", "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    # 5. Update metadata.json status
    meta_file = insp_dir / "metadata.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)

            # Map OverallStatus to UI Status
            status_map = {
                "COMPLIANT": "Compliant",
                "NON_COMPLIANT": "Non-Compliant",
                "NEEDS_REVIEW": "Needs Review"
            }
            meta["status"] = status_map.get(compliance_result.overall_status, "Needs Review")
            meta["evaluated_at"] = datetime.now(timezone.utc).isoformat()
            meta["compliance_summary"] = compliance_result.summary.model_dump()

            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update metadata status for inspection {inspection_id}: {e}")

    logger.info(f"Compliance evaluation complete for {inspection_id}: Overall = {compliance_result.overall_status}")
    return compliance_result
