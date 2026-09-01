import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI

from backend.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL
from backend.models.schemas import (
    OCRRegion,
    Evidence,
    ImageCoverage,
    ExtractedField,
    ProductFields,
    OtherDetectedInfoItem,
    AmbiguityItem,
    ConflictItem,
    CandidateValue,
    StructuredProductData,
    ImageType
)

logger = logging.getLogger("metracheck_nemotron")

_client: Optional[OpenAI] = None


def get_nemotron_client() -> Optional[OpenAI]:
    """
    Get or initialize the reusable OpenAI-compatible client for NVIDIA Nemotron.
    """
    global _client
    if _client is not None:
        return _client

    api_key = NVIDIA_API_KEY
    if not api_key:
        logger.info("NVIDIA_API_KEY not configured. Normalization will use semantic fallback parser.")
        return None

    try:
        _client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=api_key,
            timeout=12.0,
            max_retries=0
        )
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize NVIDIA OpenAI client: {e}")
        return None


NEMOTRON_SYSTEM_PROMPT = """You are an OCR semantic normalization engine for MetraCheck Legal Metrology Inspection System.

Your task is to transform OCR observations into structured product information.

You may normalize formatting, units, dates, currency, abbreviations, and obvious OCR formatting errors.

You MUST NOT invent information that is not supported by the OCR observations.

You MUST preserve uncertainty.

You MUST preserve source evidence for every extracted field.

You MUST NOT make legal compliance decisions.

You MUST NOT determine whether a Legal Metrology rule is satisfied.

If an image contains multiple distinct functional sections (e.g. pricing/MRP, nutrition facts, ingredients, FSSAI/regulatory, manufacturer details), classify image_type as "mixed_panel".

Return only the requested structured JSON matching schema_version 1.0."""

NORMALIZATION_USER_TEMPLATE = """Inspection ID: {inspection_id}

Raw OCR Observations:
{ocr_json}

INSTRUCTIONS:
1. Classify image coverage:
   - image_type (front_panel, back_panel, side_panel, nutrition_panel, ingredients_panel, mrp_panel, manufacturer_panel, importer_panel, barcode_panel, mixed_panel, unknown).
   - If multiple distinct sections are visible (e.g. MRP + Nutrition + FSSAI), classify as "mixed_panel".
   - list visible_sections (e.g. "pricing_and_mrp", "nutrition_information", "serving_size", "ingredients_list", "manufacturer_details", "regulatory_information").
2. For each field (commodity_name, manufacturer, packer, importer, manufacturer_address, packer_address, importer_address, country_of_origin, net_quantity, number_of_items, mrp, manufacturing_date, packing_date, expiry_date, best_before, consumer_care, consumer_care_phone, consumer_care_email):
   - If present: extract normalized value, set status="extracted", preserve full evidence array with image_id, source_text, ocr_confidence, bbox.
   - If partial/unclear (e.g. 'NET WT 5'): set status="ambiguous", value=5, unit=null, and record in ambiguities list.
   - If conflicting (e.g. 'MRP ₹120' and 'MRP ₹150'): set status="conflicting", value=null, record candidates in field and conflicts list.
   - If not observed in supplied OCR: set status="not_observed", value=null, evidence=[]. Do NOT assume it is missing from the actual product.
3. For date fields, extract ISO or month precision (e.g. '2026-06' with precision='month').
4. Put non-standard declarations (nutrients, energy, protein, sugars, fat, ingredients, FSSAI) into other_detected_information.
5. Return ONLY a valid JSON object matching the StructuredProductData schema. No conversational prose."""


def clean_json_response(raw_text: str) -> str:
    """
    Extracts raw JSON string from LLM response text, handling thinking tokens or markdown blocks.
    """
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        if "```" in text:
            text = text.split("```", 1)[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]

    text = text.strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        text = text[start_idx:end_idx + 1]

    return text


def extract_evidence(token: OCRRegion, default_image_id: str = "IMG-001") -> Evidence:
    return Evidence(
        image_id=token.image_id or default_image_id,
        source_text=token.text,
        ocr_confidence=token.confidence,
        bbox=token.bbox
    )


# -------------------------------------------------------------------
# Fallback Semantic Normalizer (Deterministic Rule & Pattern Matching)
# -------------------------------------------------------------------

def fallback_semantic_normalize(
    ocr_tokens: List[OCRRegion],
    inspection_id: str
) -> StructuredProductData:
    """
    High-precision, deterministic semantic normalizer producing strict StructuredProductData (schema v1.0).
    Guarantees evidence preservation, non-hallucination, and image coverage classification.
    """
    tokens_by_image: Dict[str, List[OCRRegion]] = {}
    for t in ocr_tokens:
        img_id = t.image_id or "IMG-001"
        if img_id not in tokens_by_image:
            tokens_by_image[img_id] = []
        tokens_by_image[img_id].append(t)

    images_coverage: List[ImageCoverage] = []

    for img_id, img_tokens in tokens_by_image.items():
        all_text = " ".join(t.text.lower() for t in img_tokens)
        visible_sections = []
        distinct_categories = set()

        is_nutrition = any(k in all_text for k in ["nutrition", "nutritional", "energy", "protein", "carbohydrate", "fat", "sugar", "sodium", "per 100g", "per serve"])
        is_serving = "serving size" in all_text or "per serve" in all_text
        is_ingredients = any(k in all_text for k in ["ingredients", "contains", "allergen", "added flavour"])
        is_mrp = any(k in all_text for k in ["mrp", "max retail price", "rs.", "₹", "incl. of all taxes", "unit sale price", "usp"])
        is_mfg = any(k in all_text for k in ["manufactured by", "mfg by", "packed by", "pkd by", "marketed by", "importer", "consumer care", "toll free"])
        is_fssai = any(k in all_text for k in ["fssai", "lic no", "lic. no", "890", "barcode"])

        if is_nutrition:
            visible_sections.append("nutrition_information")
            distinct_categories.add("nutrition")
        if is_serving:
            visible_sections.append("serving_size")
        if is_ingredients:
            visible_sections.append("ingredients_list")
            distinct_categories.add("ingredients")
        if is_mrp:
            visible_sections.append("pricing_and_mrp")
            distinct_categories.add("pricing")
        if is_mfg:
            visible_sections.append("manufacturer_details")
            distinct_categories.add("manufacturer")
        if is_fssai:
            visible_sections.append("regulatory_information")
            distinct_categories.add("regulatory")

        img_type: ImageType = "unknown"
        # Mixed panel classification when multiple distinct functional sections are present
        if len(distinct_categories) >= 3:
            img_type = "mixed_panel"
        elif len(distinct_categories) == 2:
            if distinct_categories == {"pricing", "manufacturer"}:
                img_type = "back_panel"
            else:
                img_type = "mixed_panel"
        elif len(distinct_categories) == 1:
            if "nutrition" in distinct_categories:
                img_type = "nutrition_panel"
            elif "ingredients" in distinct_categories:
                img_type = "ingredients_panel"
            elif "pricing" in distinct_categories:
                img_type = "mrp_panel"
            elif "manufacturer" in distinct_categories:
                img_type = "manufacturer_panel"
            elif "regulatory" in distinct_categories:
                img_type = "barcode_panel"
        elif any(k in all_text for k in ["net wt", "brand", "pure", "fresh"]):
            img_type = "front_panel"

        images_coverage.append(ImageCoverage(
            image_id=img_id,
            image_type=img_type,
            visibility_confidence=0.95 if visible_sections else 0.75,
            visible_sections=visible_sections
        ))

    prod = ProductFields()
    other_info: List[OtherDetectedInfoItem] = []
    ambiguities: List[AmbiguityItem] = []
    conflicts: List[ConflictItem] = []

    mrp_candidates: List[CandidateValue] = []
    usp_evidence: List[Evidence] = []
    net_qty_candidates: List[CandidateValue] = []
    mfg_evidence: List[Evidence] = []
    mfg_names: List[str] = []
    pkr_evidence: List[Evidence] = []
    pkr_names: List[str] = []
    imp_evidence: List[Evidence] = []
    imp_names: List[str] = []
    coo_evidence: List[Evidence] = []
    coo_val: Optional[str] = None
    commodity_evidence: List[Evidence] = []
    commodity_val: Optional[str] = None
    mfg_date_ev: List[Evidence] = []
    mfg_date_val: Optional[str] = None
    mfg_date_precision: Optional[str] = None
    exp_date_ev: List[Evidence] = []
    exp_date_val: Optional[str] = None
    best_before_ev: List[Evidence] = []
    best_before_val: Optional[str] = None
    cc_evidence: List[Evidence] = []
    cc_phone_ev: List[Evidence] = []
    cc_phone_val: Optional[str] = None
    cc_email_ev: List[Evidence] = []
    cc_email_val: Optional[str] = None

    for token in ocr_tokens:
        text = token.text.strip()
        text_lower = text.lower()
        ev = extract_evidence(token)

        # Nutrients & Ingredients
        if any(n in text_lower for n in ["energy", "protein", "carbohydrate", "total sugar", "added sugar", "fat", "saturated fat", "trans fat", "sodium", "cholesterol"]):
            val_match = re.search(r'([0-9]+(?:\.[0-9]+)?\s*(?:kcal|kJ|g|mg|mcg|%)?)', text, re.IGNORECASE)
            other_info.append(OtherDetectedInfoItem(
                category="nutrition",
                label=text.split(":")[0].strip() if ":" in text else text,
                value=val_match.group(1) if val_match else text,
                evidence=[ev]
            ))
            continue

        if "fssai" in text_lower or "lic no" in text_lower or "lic. no" in text_lower:
            lic_match = re.search(r'([0-9]{14})', text)
            other_info.append(OtherDetectedInfoItem(
                category="regulatory",
                label="FSSAI License",
                value=lic_match.group(1) if lic_match else text,
                evidence=[ev]
            ))
            continue

        # Unit Sale Price (USP)
        if any(k in text_lower for k in ["unit sale price", "usp", "per g", "per kg", "per ml", "per l", "/ g", "/ kg", "/ ml", "/ l", "/ piece"]):
            usp_evidence.append(ev)
            other_info.append(OtherDetectedInfoItem(
                category="pricing",
                label="Unit Sale Price (USP)",
                value=text,
                evidence=[ev]
            ))
            continue

        # MRP Extraction & Normalization
        if any(k in text_lower for k in ["mrp", "m.r.p", "max retail price", "maximum retail price", "rs.", "₹", "rate"]):
            match = re.search(r'(?:mrp|m\.r\.p\.?|max(?:imum)?\s*retail\s*price|rate)?\s*[:\.\s]*(?:rs\.?|₹|inr)?\s*([0-9]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
            if match and match.group(1):
                try:
                    val = float(match.group(1))
                    mrp_candidates.append(CandidateValue(value=val, evidence=ev))
                except ValueError:
                    pass

        # Net Quantity Extraction & Normalization
        if any(k in text_lower for k in ["net wt", "net weight", "net vol", "net volume", "net qty", "net quantity", "quantity", "weight"]):
            match = re.search(r'(?:net\s*(?:wt|weight|vol|volume|qty|quantity)?[:\.\s]*)?([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?', text, re.IGNORECASE)
            if match and match.group(1):
                val_str = match.group(1)
                unit_str = match.group(2)
                try:
                    val = float(val_str)
                    net_qty_candidates.append(CandidateValue(
                        value={"val": val, "unit": unit_str},
                        evidence=ev
                    ))
                except ValueError:
                    pass
        elif re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)\b', text, re.IGNORECASE):
            match = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)\b', text, re.IGNORECASE)
            if match and match.group(1):
                val_str = match.group(1)
                unit_str = match.group(2)
                if unit_str and unit_str.lower() in ["kg", "kgs", "g", "gm", "gms", "grams", "gram", "ml", "mls", "l", "ltr", "litres", "liters", "pcs", "pieces", "units"]:
                    try:
                        val = float(val_str)
                        net_qty_candidates.append(CandidateValue(
                            value={"val": val, "unit": unit_str},
                            evidence=ev
                        ))
                    except ValueError:
                        pass

        # Manufacturer / Packer / Importer
        if any(k in text_lower for k in ["manufactured by", "mfg by", "mfg & packed", "manufacturer", "co-op", "pvt ltd", "ltd.", "industries", "foods"]):
            mfg_evidence.append(ev)
            mfg_names.append(text)
        elif any(k in text_lower for k in ["packed by", "pkd by", "packer"]):
            pkr_evidence.append(ev)
            pkr_names.append(text)
        elif any(k in text_lower for k in ["imported by", "importer"]):
            imp_evidence.append(ev)
            imp_names.append(text)

        # Country of Origin
        if any(k in text_lower for k in ["country of origin", "made in", "product of", "origin:", "india"]):
            coo_evidence.append(ev)
            coo_val = "INDIA" if "india" in text_lower else text

        # Commodity / Generic Name
        if any(k in text_lower for k in ["generic name", "commodity", "product name", "milk", "tea", "biscuit", "flour", "oil", "juice", "shampoo", "soap", "atta"]):
            commodity_evidence.append(ev)
            commodity_val = text.replace("Generic Name:", "").replace("Product Name:", "").strip()

        # Dates & Shelf Life
        if any(k in text_lower for k in ["mfd", "mfg date", "packed on", "pkd"]):
            mfg_date_ev.append(ev)
            m_my = re.search(r'\b(0[1-9]|1[0-2])\s*[\/\.-]\s*(20[2-9][0-9])\b', text)
            m_dmy = re.search(r'\b([0-3]?[0-9])\s*[\/\.-]\s*(0[1-9]|1[0-2])\s*[\/\.-]\s*(20[2-9][0-9])\b', text)
            if m_dmy:
                mfg_date_val = f"{m_dmy.group(3)}-{int(m_dmy.group(2)):02d}-{int(m_dmy.group(1)):02d}"
                mfg_date_precision = "day"
            elif m_my:
                mfg_date_val = f"{m_my.group(2)}-{int(m_my.group(1)):02d}"
                mfg_date_precision = "month"
            else:
                mfg_date_val = text
                mfg_date_precision = "unspecified"

        if any(k in text_lower for k in ["use by", "exp date", "expiry"]):
            exp_date_ev.append(ev)
            exp_date_val = text

        if "best before" in text_lower:
            best_before_ev.append(ev)
            best_before_val = text

        # Consumer Care Helpline
        if any(k in text_lower for k in ["consumer", "customer care", "helpline", "toll free", "care@", "feedback@", "call:"]):
            cc_evidence.append(ev)
            phone_m = re.search(r'(?:toll free|phone|tel|call)?[:\s]*([0-9]{3,4}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4})', text, re.IGNORECASE)
            email_m = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)
            if phone_m:
                cc_phone_val = phone_m.group(1).replace(" ", "-")
                cc_phone_ev.append(ev)
            if email_m:
                cc_email_val = email_m.group(1)
                cc_email_ev.append(ev)

    # MRP
    if mrp_candidates:
        unique_vals = {}
        for c in mrp_candidates:
            v = c.value
            if v not in unique_vals:
                unique_vals[v] = []
            unique_vals[v].append(c.evidence)

        if len(unique_vals) == 1:
            val, ev_list = next(iter(unique_vals.items()))
            prod.mrp = ExtractedField[float](
                value=val,
                currency="INR",
                status="extracted",
                evidence=ev_list
            )
        else:
            candidates_list = [
                CandidateValue(value=v, evidence=evs[0])
                for v, evs in unique_vals.items()
            ]
            all_evs = [ev for evs in unique_vals.values() for ev in evs]
            prod.mrp = ExtractedField[float](
                value=None,
                currency="INR",
                status="conflicting",
                evidence=all_evs,
                candidates=candidates_list
            )
            conflicts.append(ConflictItem(
                field="mrp",
                description=f"Multiple conflicting MRP values detected: {[c.value for c in candidates_list]}",
                candidates=candidates_list
            ))

    # Net Quantity
    if net_qty_candidates:
        first = net_qty_candidates[0]
        raw_val = first.value.get("val")
        raw_unit = first.value.get("unit")

        std_unit = None
        if raw_unit:
            u_lower = raw_unit.lower()
            if u_lower in ["g", "gm", "gms", "grams", "gram"]: std_unit = "g"
            elif u_lower in ["kg", "kgs", "kilograms", "kilogram"]: std_unit = "kg"
            elif u_lower in ["ml", "mls", "millilitres", "milliliters", "millilitre"]: std_unit = "mL"
            elif u_lower in ["l", "ltr", "ltrs", "litres", "liters", "litre"]: std_unit = "L"
            elif u_lower in ["mg"]: std_unit = "mg"
            elif u_lower in ["cm"]: std_unit = "cm"
            elif u_lower in ["mm"]: std_unit = "mm"
            elif u_lower in ["pcs", "pieces", "units"]: std_unit = "units"
            else: std_unit = raw_unit

        all_ev = [c.evidence for c in net_qty_candidates]

        if std_unit:
            prod.net_quantity = ExtractedField[float](
                value=raw_val,
                unit=std_unit,
                status="extracted",
                evidence=all_ev
            )
        else:
            prod.net_quantity = ExtractedField[float](
                value=raw_val,
                unit=None,
                status="ambiguous",
                evidence=all_ev
            )
            ambiguities.append(AmbiguityItem(
                field="net_quantity",
                description=f"Net quantity numeral {raw_val} detected without unambiguous standard metric unit.",
                evidence=all_ev
            ))

    # Manufacturer & Packer
    if mfg_evidence:
        prod.manufacturer = ExtractedField[str](
            value=" ".join(mfg_names),
            status="extracted",
            evidence=mfg_evidence
        )
        prod.manufacturer_address = ExtractedField[str](
            value=" ".join(mfg_names),
            status="extracted",
            evidence=mfg_evidence
        )

    if pkr_evidence:
        prod.packer = ExtractedField[str](
            value=" ".join(pkr_names),
            status="extracted",
            evidence=pkr_evidence
        )
        prod.packer_address = ExtractedField[str](
            value=" ".join(pkr_names),
            status="extracted",
            evidence=pkr_evidence
        )

    if imp_evidence:
        prod.importer = ExtractedField[str](
            value=" ".join(imp_names),
            status="extracted",
            evidence=imp_evidence
        )

    # Country of Origin
    if coo_evidence:
        prod.country_of_origin = ExtractedField[str](
            value=coo_val or "INDIA",
            status="extracted",
            evidence=coo_evidence
        )

    # Commodity Name
    if commodity_evidence:
        prod.commodity_name = ExtractedField[str](
            value=commodity_val or commodity_evidence[0].source_text,
            status="extracted",
            evidence=commodity_evidence
        )

    # Date Information
    if mfg_date_ev:
        prod.manufacturing_date = ExtractedField[str](
            value=mfg_date_val,
            precision=mfg_date_precision,
            status="extracted",
            evidence=mfg_date_ev
        )

    if exp_date_ev:
        prod.expiry_date = ExtractedField[str](
            value=exp_date_val,
            status="extracted",
            evidence=exp_date_ev
        )

    if best_before_ev:
        prod.best_before = ExtractedField[str](
            value=best_before_val,
            status="extracted",
            evidence=best_before_ev
        )

    # Consumer Care Details
    if cc_evidence:
        prod.consumer_care = ExtractedField[str](
            value="Consumer Grievance Cell",
            status="extracted",
            evidence=cc_evidence
        )

    if cc_phone_ev:
        prod.consumer_care_phone = ExtractedField[str](
            value=cc_phone_val,
            status="extracted",
            evidence=cc_phone_ev
        )

    if cc_email_ev:
        prod.consumer_care_email = ExtractedField[str](
            value=cc_email_val,
            status="extracted",
            evidence=cc_email_ev
        )

    return StructuredProductData(
        schema_version="1.0",
        inspection_id=inspection_id,
        images=images_coverage,
        product=prod,
        other_detected_information=other_info,
        ambiguities=ambiguities,
        conflicts=conflicts
    )


# -------------------------------------------------------------------
# Primary Normalization Service with NVIDIA Nemotron
# -------------------------------------------------------------------

def normalize_ocr_with_nemotron(
    ocr_tokens: List[OCRRegion],
    inspection_id: str
) -> StructuredProductData:
    """
    Main normalization entry point:
    1. Validates OCR input.
    2. Dispatches OCR observations to NVIDIA Nemotron.
    3. Validates and parses the structured response into StructuredProductData.
    4. Falls back gracefully to deterministic semantic parser if API key is missing or endpoint is unavailable.
    """
    if not ocr_tokens:
        logger.info(f"Empty OCR token list for inspection {inspection_id}. Returning empty StructuredProductData.")
        return StructuredProductData(
            schema_version="1.0",
            inspection_id=inspection_id,
            images=[ImageCoverage(image_id="IMG-001", image_type="unknown", visibility_confidence=0.0, visible_sections=[])],
            product=ProductFields(),
            other_detected_information=[],
            ambiguities=[],
            conflicts=[]
        )

    client = get_nemotron_client()
    if client is not None:
        ocr_payload = [
            {
                "text": t.text,
                "confidence": t.confidence,
                "bbox": t.bbox,
                "image_id": t.image_id or "IMG-001"
            }
            for t in ocr_tokens
        ]

        user_prompt = NORMALIZATION_USER_TEMPLATE.format(
            inspection_id=inspection_id,
            ocr_json=json.dumps(ocr_payload, ensure_ascii=False, indent=2)
        )

        models_to_try = [
            NVIDIA_MODEL,
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3.5-lightning-30b-a3b"
        ]

        for model_candidate in models_to_try:
            try:
                logger.info(f"Dispatching {len(ocr_tokens)} OCR tokens to NVIDIA ({model_candidate})...")
                response = client.chat.completions.create(
                    model=model_candidate,
                    messages=[
                        {"role": "system", "content": NEMOTRON_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=3000
                )

                choice = response.choices[0]
                raw_content = choice.message.content or ""
                json_text = clean_json_response(raw_content)
                
                parsed_data = json.loads(json_text)
                structured_result = StructuredProductData.model_validate(parsed_data)
                logger.info(f"Successfully normalized inspection {inspection_id} with NVIDIA {model_candidate}.")
                return structured_result

            except Exception as e:
                logger.warning(f"Call to {model_candidate} failed: {e}. Trying next option...")

    # Fallback to deterministic semantic normalizer
    return fallback_semantic_normalize(ocr_tokens, inspection_id)
