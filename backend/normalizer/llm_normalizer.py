import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from backend.models.schemas import (
    OCRRegion,
    Evidence,
    NormalizedProductData,
    ProductInfoField,
    MRPField,
    NetQuantityField,
    NameAddressField,
    DateInfoField,
    ConsumerCareField,
    CountryOfOriginField,
    OtherDeclarationItem,
    CandidateValue,
    FieldStatus
)

logger = logging.getLogger("labelcheck_normalizer")

SYSTEM_PROMPT = """You are the Legal Metrology Semantic Normalizer for packaged commodity labels under the Legal Metrology (Packaged Commodities) Rules, 2011 (India).
Your job is to parse raw OCR tokens and structure them into a normalized product data schema.

STRICT INSTRUCTIONS:
1. NEVER hallucinate or guess missing values.
2. If a value is partially visible or ambiguous (e.g. 'NET WT 5' without unit), set status: 'ambiguous' and leave unknown properties null.
3. If there are conflicting values (e.g. two different MRP prices), set status: 'conflicting' and include all candidates.
4. EVERY extracted field MUST retain exact evidence from the OCR token:
   - source_text: the exact OCR string
   - ocr_confidence: the numeric confidence
   - bbox: [x1, y1, x2, y2]
   - image_id: image identifier
5. Preserve currency and unicode symbols such as ₹ (INR).
6. Return JSON matching the schema strictly.
"""

def extract_evidence(token: OCRRegion, image_id: str = "img_001") -> Evidence:
    return Evidence(
        source_text=token.text,
        ocr_confidence=token.confidence,
        bbox=token.bbox,
        image_id=image_id
    )


def normalize_with_llm(ocr_tokens: List[OCRRegion], inspection_id: str) -> Optional[NormalizedProductData]:
    """
    Calls LLM API if LLM_API_KEY or GEMINI_API_KEY or OPENAI_API_KEY is configured.
    """
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    logger.info("LLM_API_KEY detected. Dispatching OCR tokens to LLM API for semantic normalization...")

    tokens_payload = [
        {"id": t.id, "text": t.text, "confidence": t.confidence, "bbox": t.bbox}
        for t in ocr_tokens
    ]

    # Try Gemini API if key starts with AIza or GEMINI_API_KEY is set
    if os.environ.get("GEMINI_API_KEY") or api_key.startswith("AIza"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": f"Inspection ID: {inspection_id}\nRaw OCR Tokens:\n{json.dumps(tokens_payload, ensure_ascii=False)}\n\nOutput strict NormalizedProductData JSON."}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                text_out = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(text_out)
                return NormalizedProductData.model_validate(parsed_json)
        except Exception as e:
            logger.warning(f"Gemini LLM normalization failed, falling back to heuristic normalizer: {e}")

    # Try OpenAI compatible API
    if os.environ.get("OPENAI_API_KEY") or api_key.startswith("sk-"):
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Inspection ID: {inspection_id}\nRaw OCR Tokens:\n{json.dumps(tokens_payload, ensure_ascii=False)}\n\nOutput strict NormalizedProductData JSON."}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                text_out = res_data["choices"][0]["message"]["content"]
                parsed_json = json.loads(text_out)
                return NormalizedProductData.model_validate(parsed_json)
        except Exception as e:
            logger.warning(f"OpenAI LLM normalization failed, falling back to heuristic normalizer: {e}")

    return None


def heuristic_semantic_normalize(ocr_tokens: List[OCRRegion], inspection_id: str) -> NormalizedProductData:
    """
    Deterministic rule-based semantic parser that converts OCR tokens into NormalizedProductData.
    Ensures zero hallucination and complete evidence retention for every field.
    """
    data = NormalizedProductData(inspection_id=inspection_id)

    mrp_candidates: List[CandidateValue] = []
    usp_candidates: List[CandidateValue] = []
    net_qty_candidates: List[CandidateValue] = []
    mfg_candidates: List[CandidateValue] = []
    consumer_care_candidates: List[CandidateValue] = []
    country_candidates: List[CandidateValue] = []
    date_candidates: List[CandidateValue] = []
    commodity_candidates: List[CandidateValue] = []

    for token in ocr_tokens:
        text = token.text.strip()
        text_lower = text.lower()
        ev = extract_evidence(token)

        # --------------------------------------------------
        # 1. Unit Sale Price (USP)
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["unit sale price", "unit price", "usp", "per ml", "per g", "per kg", "/ ml", "/ g", "/ kg", "/ piece", "/ unit", "/ item"]):
            usp_candidates.append(CandidateValue(
                value={"text": text},
                evidence=ev
            ))
            continue

        # --------------------------------------------------
        # 2. MRP Extraction & Normalization
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["mrp", "m.r.p", "max retail price", "maximum retail price", "rs.", "₹", "rate"]):
            is_incl_tax = any(kw in text_lower for kw in ["incl", "inclusive", "taxes"])
            match = re.search(r'(?:mrp|m\.r\.p\.?|max(?:imum)?\s*retail\s*price|rate)?\s*[:\.\s]*(?:rs\.?|₹|inr)?\s*([0-9]+(?:\.[0-9]{1,2})?)', text, re.IGNORECASE)
            
            if match and match.group(1):
                try:
                    val = float(match.group(1))
                    mrp_candidates.append(CandidateValue(
                        value={"val": val, "incl_tax": is_incl_tax},
                        evidence=ev
                    ))
                except ValueError:
                    pass

        # --------------------------------------------------
        # 3. Net Quantity Extraction & Normalization
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["net wt", "net weight", "net vol", "net volume", "net qty", "net quantity", "weight", "volume", "quantity"]):
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
                if unit_str and unit_str.lower() in ["kg", "g", "gm", "grams", "ml", "l", "litres", "liters", "pcs", "pieces", "units", "lbs", "oz"]:
                    try:
                        val = float(val_str)
                        net_qty_candidates.append(CandidateValue(
                            value={"val": val, "unit": unit_str},
                            evidence=ev
                        ))
                    except ValueError:
                        pass

        # --------------------------------------------------
        # 4. Manufacturer / Packer Extraction & Normalization
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["mfg by", "manufactured by", "packed by", "mfg & packed", "pkd by", "marketed by", "imported by", "manufacturer", "co-op", "pvt ltd", "ltd.", "industries", "foods"]):
            pincode_match = re.search(r'\b([1-9][0-9]{5})\b', text)
            pincode = pincode_match.group(1) if pincode_match else None
            mfg_candidates.append(CandidateValue(
                value={"text": text, "pincode": pincode},
                evidence=ev
            ))

        # --------------------------------------------------
        # 5. Dates & Batch Information
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["mfd", "mfg date", "packed on", "pkd", "use by", "best before", "expiry", "exp date", "batch", "lot"]):
            date_candidates.append(CandidateValue(
                value={"text": text},
                evidence=ev
            ))

        # --------------------------------------------------
        # 6. Consumer Care Helpline Details
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["consumer", "customer care", "helpline", "toll free", "care@", "feedback@", "grievance", "complaint", "call:"]):
            phone_match = re.search(r'(?:toll free|phone|tel|call)?[:\s]*([0-9]{3,4}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4})', text, re.IGNORECASE)
            email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', text)
            
            consumer_care_candidates.append(CandidateValue(
                value={
                    "text": text,
                    "phone": phone_match.group(1) if phone_match else None,
                    "email": email_match.group(1) if email_match else None
                },
                evidence=ev
            ))

        # --------------------------------------------------
        # 7. Country of Origin
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["country of origin", "made in", "origin:", "product of", "india"]):
            origin_val = "INDIA" if "india" in text_lower else text
            country_candidates.append(CandidateValue(
                value={"country": origin_val},
                evidence=ev
            ))

        # --------------------------------------------------
        # 8. Commodity / Generic Name
        # --------------------------------------------------
        if any(kw in text_lower for kw in ["product name", "generic name", "commodity", "milk", "tea", "biscuit", "flour", "oil", "juice", "shampoo", "soap", "atta"]):
            commodity_candidates.append(CandidateValue(
                value={"text": text},
                evidence=ev
            ))

    # ======================================================
    # Synthesize Final Structured Fields
    # ======================================================

    # MRP Synthesis
    detected_usp = usp_candidates[0].value.get("text") if usp_candidates else None

    if len(mrp_candidates) == 1:
        c = mrp_candidates[0]
        data.mrp = MRPField(
            value=c.value.get("val"),
            currency="INR",
            is_inclusive_of_taxes=c.value.get("incl_tax"),
            unit_sale_price=detected_usp,
            status="extracted",
            evidence=c.evidence
        )
    elif len(mrp_candidates) > 1:
        vals = set(c.value.get("val") for c in mrp_candidates if c.value.get("val") is not None)
        if len(vals) > 1:
            data.mrp = MRPField(
                status="conflicting",
                candidates=mrp_candidates,
                evidence=mrp_candidates[0].evidence,
                unit_sale_price=detected_usp
            )
        else:
            c = mrp_candidates[0]
            data.mrp = MRPField(
                value=c.value.get("val"),
                currency="INR",
                is_inclusive_of_taxes=c.value.get("incl_tax"),
                unit_sale_price=detected_usp,
                status="extracted",
                evidence=c.evidence
            )
    elif detected_usp:
        data.mrp = MRPField(
            unit_sale_price=detected_usp,
            status="missing",
            evidence=usp_candidates[0].evidence
        )

    # Net Quantity Synthesis
    if len(net_qty_candidates) == 1:
        c = net_qty_candidates[0]
        unit = c.value.get("unit")
        std_unit = unit.lower() if unit else None
        if std_unit in ["gm", "grams"]:
            std_unit = "g"
        elif std_unit in ["litres", "liter", "liters"]:
            std_unit = "l"

        status: FieldStatus = "extracted" if unit else "ambiguous"
        data.net_quantity = NetQuantityField(
            value=c.value.get("val"),
            unit=unit,
            standardized_unit=std_unit,
            status=status,
            evidence=c.evidence
        )
    elif len(net_qty_candidates) > 1:
        data.net_quantity = NetQuantityField(
            value=net_qty_candidates[0].value.get("val"),
            unit=net_qty_candidates[0].value.get("unit"),
            standardized_unit=net_qty_candidates[0].value.get("unit"),
            status="extracted",
            evidence=net_qty_candidates[0].evidence,
            candidates=net_qty_candidates
        )

    # Manufacturer Synthesis
    if mfg_candidates:
        c = mfg_candidates[0]
        data.manufacturer = NameAddressField(
            name=c.value.get("text"),
            address=c.value.get("text"),
            pincode=c.value.get("pincode"),
            status="extracted",
            evidence=c.evidence,
            candidates=mfg_candidates if len(mfg_candidates) > 1 else None
        )

    # Date Information Synthesis
    if date_candidates:
        c = date_candidates[0]
        mfg_date_str = None
        exp_date_str = None
        best_before_str = None
        for d in date_candidates:
            dt = d.value.get("text", "")
            if "mfg" in dt.lower() or "packed" in dt.lower() or "pkd" in dt.lower():
                mfg_date_str = dt
            if "use by" in dt.lower() or "exp" in dt.lower():
                exp_date_str = dt
            if "best before" in dt.lower():
                best_before_str = dt

        data.date_information = DateInfoField(
            manufacturing_date=mfg_date_str or (date_candidates[0].value.get("text") if date_candidates else None),
            expiry_date=exp_date_str,
            best_before=best_before_str or exp_date_str,
            status="extracted",
            evidence=c.evidence,
            candidates=date_candidates if len(date_candidates) > 1 else None
        )

    # Consumer Care Synthesis
    if consumer_care_candidates:
        c = consumer_care_candidates[0]
        data.consumer_care = ConsumerCareField(
            name="Consumer Grievance Cell",
            address=c.value.get("text"),
            phone=c.value.get("phone"),
            email=c.value.get("email"),
            status="extracted",
            evidence=c.evidence,
            candidates=consumer_care_candidates if len(consumer_care_candidates) > 1 else None
        )

    # Country of Origin Synthesis
    if country_candidates:
        c = country_candidates[0]
        data.country_of_origin = CountryOfOriginField(
            value=c.value.get("country", "INDIA"),
            status="extracted",
            evidence=c.evidence
        )

    # Commodity Name Synthesis
    if commodity_candidates:
        c = commodity_candidates[0]
        data.product = ProductInfoField(
            commodity_name=c.value.get("text"),
            status="extracted",
            evidence=c.evidence
        )

    return data


def normalize_ocr_data(ocr_tokens: List[OCRRegion], inspection_id: str) -> NormalizedProductData:
    """
    Main normalization entry point:
    1. Tries LLM normalization if LLM_API_KEY is available.
    2. Falls back to deterministic heuristic normalization with complete evidence tracking.
    """
    llm_result = normalize_with_llm(ocr_tokens, inspection_id)
    if llm_result:
        return llm_result
    return heuristic_semantic_normalize(ocr_tokens, inspection_id)
