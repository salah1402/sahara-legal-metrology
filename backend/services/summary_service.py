import os
import re
import logging
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

from backend.models.compliance import ComplianceResult
from backend.models.schemas import StructuredProductData

load_dotenv()
logger = logging.getLogger("sahara_summary_service")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

# Blacklist patterns to strictly prevent internal prompt/reasoning leakage into PDF reports
PROMPT_LEAKAGE_PATTERNS = [
    r"user\s+wants",
    r"system\s+prompt",
    r"user\s+prompt",
    r"as\s+an?\s+ai",
    r"as\s+a\s+language\s+model",
    r"here\s+is\s+(?:a|the)\s+summary",
    r"sure,\s+here",
    r"task\s*:",
    r"strict\s+constraints",
    r"do\s+not\s+(?:change|invent|contradict)",
    r"prompt\s*:",
    r"json\s+schema",
    r"i\s+need\s+to",
    r"i\s+will\s+(?:write|generate|summarize)",
    r"let['’]?s\s+summarize",
    r"instruction\s*:",
    r"developer\s+instruction",
    r"model\s+response",
    r"temperature\s*=",
    r"model\s*:",
    r"executive\s+summary\s*:"
]


def is_prompt_leakage(text: str) -> bool:
    """Detects whether raw prompts, chain-of-thought, or instructions leaked into summary text."""
    if not text or not isinstance(text, str):
        return True
    lower = text.lower().strip()
    for pattern in PROMPT_LEAKAGE_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return True
    return False


def sanitize_summary_text(text: str) -> str:
    """Removes outer markdown wrappers, quotes, and preambles."""
    if not text:
        return ""
    cleaned = text.strip()
    # Strip markdown code blocks or quotes
    cleaned = re.sub(r'^```[\w]*\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    cleaned = cleaned.strip('"\'`').strip()
    # Strip leading markdown headers like # Summary or **Summary:**
    cleaned = re.sub(r'^(?:#+|\*\*|##)\s*(?:Executive\s+)?(?:Inspection\s+)?Summary:?\s*(?:\*\*)?\s*', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def generate_deterministic_summary(
    compliance: ComplianceResult,
    commodity_name: Optional[str] = None,
    brand_or_mfg: Optional[str] = None
) -> str:
    """
    Deterministic rule-based summary generator.
    Produces a factual 2-4 sentence executive summary directly from the compliance result.
    Guaranteed to work offline without LLM dependencies.
    """
    from backend.main import clean_display_product_name
    cleaned_comm = clean_display_product_name(commodity_name) if commodity_name else ""
    cleaned_brand = clean_display_product_name(brand_or_mfg) if brand_or_mfg else ""

    if cleaned_comm and cleaned_comm != "Untitled Inspection":
        product_label = cleaned_comm
    elif cleaned_brand and cleaned_brand != "Untitled Inspection":
        product_label = cleaned_brand
    else:
        product_label = "Packaged Commodity"

    if cleaned_brand and cleaned_brand != "Untitled Inspection" and cleaned_brand.lower() not in product_label.lower():
        product_label = f"{product_label} ({cleaned_brand})"

    summary = compliance.summary
    status = compliance.overall_status

    if status == "COMPLIANT":
        return (
            f"The package label inspection for {product_label} (Inspection ID: {compliance.inspection_id}) "
            f"concluded as COMPLIANT under the Legal Metrology (Packaged Commodities) Rules, 2011. "
            f"All {summary.total_checks} statutory declarations evaluated satisfied mandatory requirements, "
            f"with {summary.passed} declarations verified against optical package evidence "
            f"and {summary.exempt + summary.not_applicable} provisions determined to be exempt or not applicable."
        )
    elif status == "NON_COMPLIANT":
        failed_rules = [c for c in compliance.checks if c.status == "FAIL"]
        failed_titles = [f"Rule {c.rule_number} ({c.title})" for c in failed_rules[:3]]
        failed_str = ", ".join(failed_titles)
        if len(failed_rules) > 3:
            failed_str += f", and {len(failed_rules) - 3} other provision(s)"

        return (
            f"The package label inspection for {product_label} (Inspection ID: {compliance.inspection_id}) "
            f"resulted in a NON-COMPLIANT determination under PCR 2011 due to {summary.failed} statutory violation(s). "
            f"Non-compliant declarations include: {failed_str}. "
            f"Out of {summary.total_checks} total checks, {summary.passed} passed, "
            f"{summary.failed} failed, and {summary.needs_review} require manual verification."
        )
    else:  # NEEDS_REVIEW
        review_rules = [c for c in compliance.checks if c.status == "NEEDS_REVIEW"]
        review_titles = [f"Rule {c.rule_number} ({c.title})" for c in review_rules[:3]]
        review_str = ", ".join(review_titles)
        if len(review_rules) > 3:
            review_str += f", and {len(review_rules) - 3} other check(s)"

        return (
            f"The package label inspection for {product_label} (Inspection ID: {compliance.inspection_id}) "
            f"resulted in NEEDS REVIEW because several mandatory declarations could not be fully verified from the supplied package images. "
            f"While {summary.passed} declaration(s) were successfully confirmed, {summary.needs_review} requirement(s) "
            f"require physical verification or additional package-panel views, including: {review_str}."
        )


def generate_inspection_summary(
    compliance: ComplianceResult,
    product_data: Optional[StructuredProductData] = None,
    display_title: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generates a concise 2-4 sentence executive summary.
    Attempts NVIDIA Nemotron 3 Ultra 550B first with strict prompt leakage filtering;
    falls back seamlessly to deterministic generation if LLM is unavailable or leaks prompt text.
    Returns (summary_text, source) where source is 'nemotron' or 'deterministic_fallback'.
    """
    commodity_name = None
    brand_or_mfg = None

    if product_data:
        if product_data.product.commodity_name.status == "extracted" and product_data.product.commodity_name.value:
            commodity_name = product_data.product.commodity_name.value
        if product_data.product.manufacturer.status == "extracted" and product_data.product.manufacturer.value:
            brand_or_mfg = product_data.product.manufacturer.value

    if not commodity_name and display_title and display_title != "Untitled Inspection":
        commodity_name = display_title

    # Try LLM Summary via NVIDIA Nemotron
    if NVIDIA_API_KEY:
        try:
            from openai import OpenAI

            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=NVIDIA_API_KEY,
                timeout=6.0,
                max_retries=1
            )

            failed_items = [f"- Rule {c.rule_number} ({c.title}): {c.reason}" for c in compliance.checks if c.status == "FAIL"]
            review_items = [f"- Rule {c.rule_number} ({c.title}): {c.reason}" for c in compliance.checks if c.status == "NEEDS_REVIEW"]
            exempt_items = [f"- Rule {c.rule_number} ({c.title}): {c.reason}" for c in compliance.checks if c.status == "EXEMPT"]

            prompt_content = f"""Product: {commodity_name or 'Packaged Commodity'}
Inspection ID: {compliance.inspection_id}
Overall Compliance Verdict: {compliance.overall_status}
Summary Stats: Total {compliance.summary.total_checks}, Passed {compliance.summary.passed}, Failed {compliance.summary.failed}, Needs Review {compliance.summary.needs_review}, Exempt {compliance.summary.exempt}, Not Applicable {compliance.summary.not_applicable}

Failed Violations:
{chr(10).join(failed_items) if failed_items else "None"}

Review Items:
{chr(10).join(review_items) if review_items else "None"}

Exempt Provisions:
{chr(10).join(exempt_items) if exempt_items else "None"}

Write a 2 to 4 sentence inspection summary paragraph. Return ONLY the final summary paragraph."""

            response = client.chat.completions.create(
                model="nvidia/nemotron-3-ultra-550b-a55b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional regulatory report summarizer for SAHARA Legal Metrology Inspection System. Output ONLY the clean 2-4 sentence summary. Do not include instructions, preambles, or thoughts."
                    },
                    {
                        "role": "user",
                        "content": prompt_content
                    }
                ],
                temperature=0.2,
                max_tokens=250
            )

            raw_text = response.choices[0].message.content
            cleaned_text = sanitize_summary_text(raw_text)

            # Check for prompt leakage or uncharacteristic output
            if cleaned_text and len(cleaned_text) >= 40 and not is_prompt_leakage(cleaned_text):
                logger.info(f"Generated clean LLM summary for {compliance.inspection_id} via Nemotron.")
                return cleaned_text, "nemotron"
            else:
                logger.warning(f"Rejected LLM summary for {compliance.inspection_id} due to prompt leakage / quality checks: '{cleaned_text[:60]}...'. Using fallback.")

        except Exception as e:
            logger.warning(f"Nemotron summary generation failed/skipped for {compliance.inspection_id}: {e}. Using deterministic fallback.")

    # Fallback
    fallback_text = generate_deterministic_summary(compliance, commodity_name, brand_or_mfg)
    return fallback_text, "deterministic_fallback"
