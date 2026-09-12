import os
import io
import base64
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import httpx
from PIL import Image, ImageOps

from backend.config import NVIDIA_API_KEY, NVIDIA_OCR_URL, OCR_PROVIDER

logger = logging.getLogger("sahara_ocr_service")

# Concurrency lock for CPU OCR fallback
_rapidocr_lock = asyncio.Lock()
_rapidocr_engine = None
_rapidocr_import_error: Optional[str] = None


def get_rapidocr_engine():
    """Lazily initializes and returns singleton RapidOCR engine only when needed."""
    global _rapidocr_engine, _rapidocr_import_error
    if _rapidocr_engine is not None:
        return _rapidocr_engine
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
        logger.info("Lazily initializing RapidOCR engine (PP-OCRv4 ONNX CPU fallback)...")
        _rapidocr_engine = RapidOCR(det_limit_side_len=640, det_limit_type="max", use_cls=False)
        logger.info("RapidOCR fallback engine initialized successfully.")
        return _rapidocr_engine
    except Exception as e:
        _rapidocr_import_error = str(e)
        logger.error(f"Failed to initialize RapidOCR fallback: {e}", exc_info=True)
        raise RuntimeError(f"RapidOCR engine unavailable: {e}")


def load_and_prepare_image_for_nemotron(image_path: Path) -> Tuple[str, int, int, str]:
    """
    Loads image, applies EXIF transposition, checks dimensions,
    and returns (base64_data_uri, orig_w, orig_h, mime_type).
    """
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img) or img
        orig_w, orig_h = img.size

        # Cap very large dimensions (> 2560px) to keep network payload fast while preserving clarity
        max_dim = 2560
        if max(orig_w, orig_h) > max_dim:
            scale = max_dim / max(orig_w, orig_h)
            new_w = max(1, int(orig_w * scale))
            new_h = max(1, int(orig_h * scale))
            img_to_send = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            img_to_send = img

        buffer = io.BytesIO()
        # Convert RGBA / P to RGB for JPEG
        if img_to_send.mode in ("RGBA", "LA", "P"):
            rgb_img = Image.new("RGB", img_to_send.size, (255, 255, 255))
            if img_to_send.mode == "RGBA":
                rgb_img.paste(img_to_send, mask=img_to_send.split()[3])
            else:
                rgb_img.paste(img_to_send)
            rgb_img.save(buffer, format="JPEG", quality=92, optimize=True)
            mime_type = "image/jpeg"
        else:
            img_to_send.convert("RGB").save(buffer, format="JPEG", quality=92, optimize=True)
            mime_type = "image/jpeg"

        b64_bytes = base64.b64encode(buffer.getvalue()).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_bytes}"

    return data_uri, orig_w, orig_h, mime_type


async def extract_nemotron_ocr(image_path: Path) -> List[Dict[str, Any]]:
    """
    Sends the image to NVIDIA's hosted Nemotron OCR v2 API.
    Parses normalized polygon bounding coordinates into absolute pixel bounding boxes [x1, y1, x2, y2].
    Converts detections into standard OCRRegion dict structures.
    """
    if not NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY is not configured in environment.")

    endpoint = NVIDIA_OCR_URL
    logger.info(f"Preparing image for NVIDIA Nemotron OCR v2: {image_path.name}")
    data_uri, orig_w, orig_h, _ = await asyncio.to_thread(load_and_prepare_image_for_nemotron, image_path)

    payload = {
        "input": [
            {
                "url": data_uri
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"Calling NVIDIA Nemotron OCR v2 endpoint: {endpoint} (Image dimensions: {orig_w}x{orig_h})")

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as te:
            logger.error(f"NVIDIA Nemotron OCR v2 request timed out: {te}")
            raise RuntimeError(f"NVIDIA Nemotron OCR v2 API timed out after 45s: {te}")
        except httpx.RequestError as re:
            logger.error(f"NVIDIA Nemotron OCR v2 network request error: {re}")
            raise RuntimeError(f"NVIDIA Nemotron OCR v2 network error: {re}")

    if response.status_code != 200:
        masked_detail = response.text[:400] if response.text else "No response body"
        logger.error(f"NVIDIA Nemotron OCR v2 returned HTTP {response.status_code}: {masked_detail}")
        raise RuntimeError(f"NVIDIA Nemotron OCR v2 API error ({response.status_code}): {masked_detail}")

    res_json = response.json()
    data_items = res_json.get("data", [])
    if not data_items:
        logger.warning("NVIDIA Nemotron OCR v2 returned empty data array.")
        return []

    text_detections = data_items[0].get("text_detections", [])
    logger.info(f"NVIDIA Nemotron OCR v2 returned {len(text_detections)} raw text detections.")

    ocr_regions: List[Dict[str, Any]] = []
    for idx, det in enumerate(text_detections):
        text_pred = det.get("text_prediction", {})
        text = str(text_pred.get("text", "")).strip()
        confidence = float(text_pred.get("confidence", 0.9))

        pts = det.get("bounding_box", {}).get("points", [])
        if pts and len(pts) >= 2:
            xs = [int(p.get("x", 0.0) * orig_w) for p in pts]
            ys = [int(p.get("y", 0.0) * orig_h) for p in pts]
            bbox = [
                max(0, min(xs)),
                max(0, min(ys)),
                min(orig_w, max(xs)),
                min(orig_h, max(ys))
            ]
        else:
            bbox = [0, 0, orig_w, orig_h]

        if not text:
            continue

        ocr_regions.append({
            "id": f"ocr_{idx + 1:03d}",
            "text": text,
            "confidence": round(confidence, 4),
            "bbox": bbox,
            "image_id": "IMG-001"
        })

    logger.info(f"Parsed {len(ocr_regions)} valid OCR regions from NVIDIA Nemotron OCR v2.")
    return ocr_regions


async def extract_rapidocr(image_path: Path) -> List[Dict[str, Any]]:
    """
    Executes local RapidOCR ONNX inference as fallback.
    """
    import numpy as np

    def _sync_rapidocr():
        engine = get_rapidocr_engine()
        with Image.open(image_path) as pil_img:
            pil_img = ImageOps.exif_transpose(pil_img) or pil_img
            orig_w, orig_h = pil_img.size
            max_dim = 720
            if max(orig_w, orig_h) > max_dim:
                scale = max_dim / max(orig_w, orig_h)
                new_w, new_h = max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
                resized = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                scale_x = orig_w / new_w
                scale_y = orig_h / new_h
                ocr_input = np.array(resized.convert("RGB"))[:, :, ::-1]
            else:
                scale_x, scale_y = 1.0, 1.0
                ocr_input = np.array(pil_img.convert("RGB"))[:, :, ::-1]

        result, _ = engine(ocr_input)
        regions = []
        if result:
            for idx, item in enumerate(result):
                pts = item[0]
                txt = str(item[1]).strip()
                score = float(item[2])
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                raw_bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
                bbox = [
                    int(raw_bbox[0] * scale_x),
                    int(raw_bbox[1] * scale_y),
                    int(raw_bbox[2] * scale_x),
                    int(raw_bbox[3] * scale_y)
                ]
                regions.append({
                    "id": f"ocr_{idx + 1:03d}",
                    "text": txt,
                    "confidence": round(score, 4),
                    "bbox": bbox,
                    "image_id": "IMG-001"
                })
        return regions

    async with _rapidocr_lock:
        return await asyncio.to_thread(_sync_rapidocr)


async def run_ocr_pipeline(image_path: Path, provider: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    """
    Unified OCR entry point.
    Routes to NVIDIA Nemotron OCR v2 hosted API when configured.
    Falls back gracefully to local RapidOCR if API is unavailable or unconfigured.
    Returns: (List[OCRRegion_dict], engine_name_str)
    """
    chosen_provider = (provider or OCR_PROVIDER or "nemotron").strip().lower()

    if chosen_provider == "nemotron":
        if NVIDIA_API_KEY:
            try:
                regions = await extract_nemotron_ocr(image_path)
                return regions, "NVIDIA Nemotron OCR v2"
            except Exception as e:
                logger.warning(f"NVIDIA Nemotron OCR v2 failed: {e}. Falling back to RapidOCR...", exc_info=True)
        else:
            logger.warning("NVIDIA_API_KEY not configured. Falling back to RapidOCR...")

    # Fallback or explicit rapidocr
    try:
        regions = await extract_rapidocr(image_path)
        engine_label = "RapidOCR (Fallback)" if chosen_provider == "nemotron" else "RapidOCR"
        return regions, engine_label
    except Exception as e:
        logger.error(f"RapidOCR fallback also failed: {e}", exc_info=True)
        raise RuntimeError(f"All OCR providers failed: {e}")
