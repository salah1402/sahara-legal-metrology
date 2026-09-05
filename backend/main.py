import os
import sys
import uuid
import json
import re
import gc
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure workspace root is in sys.path so `uvicorn main:app` inside backend/ works cleanly
_pkg_root = str(Path(__file__).resolve().parent.parent)
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

# Configure low-memory CPU runtime environment flags for RapidOCR / ONNX & BLAS
os.environ["FLAGS_eager_delete_tensor_gb"] = "0.0"
os.environ["FLAGS_fast_eager_deletion_mode"] = "1"
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sahara_backend")


def get_current_rss_mb() -> float:
    """Returns current process Resident Set Size (RAM) in megabytes."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


# --------------------------------------------------------------------
# Ultra-Lightweight ONNX OCR Engine (Render Free 512MB CPU Optimized)
# --------------------------------------------------------------------
RapidOCR = None
rapidocr_version = "not installed"
rapidocr_import_error: Optional[str] = None

try:
    from rapidocr_onnxruntime import RapidOCR  # type: ignore
    import rapidocr_onnxruntime as r_mod
    rapidocr_version = getattr(r_mod, "__version__", "1.4.x")
    logger.info(f"RapidOCR (PP-OCRv4 ONNX) imported successfully (version: {rapidocr_version})")
except Exception as e:
    rapidocr_import_error = str(e)
    logger.error(f"Failed to import RapidOCR: {e}", exc_info=True)
    RapidOCR = None

from backend.models.schemas import (
    OCRRegion,
    StructuredProductData,
)
from backend.models.compliance import ComplianceResult
from backend.services.nemotron_service import normalize_ocr_with_nemotron
from backend.services.compliance_service import run_compliance_evaluation
from backend.services.report_service import generate_inspection_pdf
from backend.services.summary_service import generate_inspection_summary

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent
INSPECTIONS_DIR = BASE_DIR / "inspections"
INSPECTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI App
app = FastAPI(
    title="SAHARA — Legal Metrology Inspection System",
    description="SAHARA Backend — Production OCR, NVIDIA Nemotron Semantic Normalization & Deterministic Legal Metrology Compliance Engine",
    version="3.1.0"
)

# Configure CORS for all origins, local development, and Vercel production hosts
cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False if "*" in allowed_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount inspections directory for static image retrieval
app.mount("/static/inspections", StaticFiles(directory=str(INSPECTIONS_DIR)), name="inspections")

# Lazy Singleton RapidOCR Engine (<100MB RAM, CPU Optimized)
_ocr_engine = None
_ocr_init_error: Optional[str] = None
ocr_lock = asyncio.Lock()


def get_ocr_engine():
    """Lazily initializes and returns the shared singleton RapidOCR engine."""
    global _ocr_engine, _ocr_init_error
    if _ocr_engine is not None:
        return _ocr_engine
    if RapidOCR is None:
        raise RuntimeError(f"RapidOCR package is not available: {rapidocr_import_error}")

    logger.info("Initializing lazy singleton RapidOCR engine (PP-OCRv4 ONNX CPU, det_limit=640, use_cls=False)...")
    try:
        _ocr_engine = RapidOCR(det_limit_side_len=640, det_limit_type="max", use_cls=False)
        logger.info(f"RapidOCR engine initialized successfully (Process RSS: {get_current_rss_mb():.1f} MB).")
        return _ocr_engine
    except Exception as e:
        _ocr_init_error = str(e)
        logger.error(f"Error initializing RapidOCR engine: {e}", exc_info=True)
        raise


@app.on_event("startup")
async def preload_ocr_engine():
    """Pre-warms RapidOCR in a worker thread so first request does not suffer cold start delays."""
    try:
        logger.info("Pre-warming RapidOCR ONNX engine in background thread...")
        await asyncio.to_thread(get_ocr_engine)
        logger.info("RapidOCR ONNX engine pre-warm completed successfully.")
    except Exception as prewarm_err:
        logger.warning(f"RapidOCR pre-warm skipped or delayed: {prewarm_err}")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def clean_product_token(token: str) -> bool:
    """Returns False if token is gibberish hash, pure number, or OCR noise."""
    t = token.strip()
    if not t:
        return False
    # If token is pure digits (e.g. '255', '3', '1080')
    if re.match(r'^\d+$', t):
        return False
    # If token is a long random alphanumeric string (hash like 'imahgycfya2yx6nn', 'd3x89v', 'a1b2c3d4')
    if len(t) >= 7 and bool(re.search(r'\d', t)) and bool(re.search(r'[a-zA-Z]', t)):
        return False
    if len(t) >= 9 and not bool(re.search(r'[aeiouAEIOU]', t)):
        return False
    # Common web/asset noise tokens
    if t.lower() in ["jpg", "png", "jpeg", "webp", "img", "image", "photo", "thumb", "thumbnail", "preview", "upload", "download"]:
        return False
    return True


def clean_display_product_name(raw_name: Optional[str]) -> str:
    """
    Cleans OCR garbage, random hash suffixes, and duplicated tokens from product names.
    Preserves auditability in backend while ensuring clean human-readable UI presentation.
    """
    if not raw_name or not str(raw_name).strip():
        return "Untitled Inspection"
    text = str(raw_name).strip()
    if text.lower() in ["untitled inspection", "untitled", "product", "image", "photo"]:
        return "Untitled Inspection"

    # Split by spaces / hyphens / underscores
    raw_tokens = re.split(r'[\s\-_\/.]+', text)
    valid_tokens = [t for t in raw_tokens if clean_product_token(t)]

    if not valid_tokens:
        return "Untitled Inspection"

    # Deduplicate consecutive or repeated words while preserving original order
    seen = set()
    deduped = []
    for t in valid_tokens:
        lower_t = t.lower()
        if lower_t not in seen:
            seen.add(lower_t)
            deduped.append(t.capitalize())

    cleaned = " ".join(deduped).strip()
    return cleaned if len(cleaned) >= 2 else "Untitled Inspection"


def clean_filename_title(filename: str) -> str:
    """
    Derives a clean, human-readable name from the uploaded filename.
    Example: 'Britannia-The-Original-Bourbon.jpg' -> 'Britannia The Original Bourbon'
             '255-original-style-chilli-sprinkled-3-bingo-original-imahgycfya2yx6nn.jpg' -> 'Original Style Chilli Sprinkled Bingo'
             'IMG_20260831_123456.jpg' -> 'Untitled Inspection'
    """
    if not filename:
        return "Untitled Inspection"
    stem = Path(filename).stem
    if re.match(r'^(?:img|dsc|photo|image|picture|sample|snapshot|p|pic|screenshot)?[\W_]*[0-9_\-\s]*$', stem, flags=re.IGNORECASE):
        return "Untitled Inspection"

    clean_no_prefix = re.sub(
        r'^(?:img|dsc|photo|image|picture|sample|snapshot)\s*[0-9_\-]*\s*',
        '',
        stem,
        flags=re.IGNORECASE
    ).strip()

    return clean_display_product_name(clean_no_prefix or stem)


def format_composite_product_title(commodity: Optional[str], brand_or_mfg: Optional[str], fallback_name: str) -> str:
    """
    Formats inspection display name following:
    <Product / Commodity Name> — <Brand / Product Name>
    Examples:
    'Bourbon Biscuits — Britannia'
    'Rice — India Gate'
    'Soap — Dove'
    """
    comm = clean_display_product_name(commodity) if commodity and commodity != "Untitled Inspection" else ""
    brand = clean_display_product_name(brand_or_mfg) if brand_or_mfg and brand_or_mfg != "Untitled Inspection" else ""

    if comm and brand and comm != "Untitled Inspection" and brand != "Untitled Inspection":
        if brand.lower() in comm.lower():
            return comm
        return f"{comm} — {brand}"
    elif comm and comm != "Untitled Inspection":
        return comm
    elif brand and brand != "Untitled Inspection":
        return brand
    return clean_filename_title(fallback_name)


def resolve_display_name(meta: Dict[str, Any]) -> str:
    """
    Strict naming priority for inspections:
    1. Explicit user-provided display_name (if set and not empty).
    2. Normalized commodity_name / composite product_name from OCR/Nemotron.
    3. 'Untitled Inspection' as the final fallback.
    NEVER uses random generated names, hash noise, or inspection IDs as display title.
    """
    if meta.get("display_name") and str(meta["display_name"]).strip():
        return str(meta["display_name"]).strip()
    if meta.get("product_name") and str(meta["product_name"]).strip() and meta["product_name"] != "Untitled Inspection":
        return clean_display_product_name(str(meta["product_name"]).strip())
    return "Untitled Inspection"


class RenameInspectionPayload(BaseModel):
    display_name: Optional[str] = Field(None, description="Human-readable display title (or null/empty to reset to auto-naming)", max_length=120)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "product": "SAHARA",
        "subtitle": "Legal Metrology Inspection System",
        "service": "SAHARA OCR, Nemotron Normalization & Legal Compliance Backend",
        "engine": "RapidOCR (PP-OCRv4 ONNX) + NVIDIA Nemotron 3 Ultra 550B + PCR 2011 Compliance Evaluator",
        "ocr_version": rapidocr_version,
        "ocr_initialized": _ocr_engine is not None,
        "ocr_error": rapidocr_import_error or _ocr_init_error,
        "phases": ["Phase 1 (Frontend)", "Phase 2 (OCR & Nemotron)", "Phase 3 (Legal Metrology Compliance Engine)", "Phase 4 (Summary & PDF)", "Phase 5 (Workstation & Mobile)"]
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ocr_engine_available": RapidOCR is not None,
        "ocr_engine_loaded": _ocr_engine is not None,
        "ocr_version": rapidocr_version,
        "ocr_error": rapidocr_import_error or _ocr_init_error,
        "process_rss_mb": round(get_current_rss_mb(), 1),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ====================================================================
# 1. OCR Ingestion Endpoint (POST /api/ocr)
# ====================================================================

@app.post("/api/ocr")
async def process_ocr(
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None),
    inspection_id_param: Optional[str] = Form(None),
    inspection_name_param: Optional[str] = Form(None)
):
    """
    POST /api/ocr
    Accepts an uploaded image file via multipart/form-data.
    Performs RapidOCR (PP-OCRv4 ONNX) detection and text recognition with low-memory CPU safeguards.
    Saves raw OCR evidence into `ocr/raw_ocr.json`.
    Returns raw OCR JSON.
    """
    if RapidOCR is None:
        err_detail = f"OCR engine package is unavailable on the server ({rapidocr_import_error})."
        logger.error(err_detail)
        raise HTTPException(status_code=500, detail=err_detail)

    target_file = file or image
    if not target_file and images and len(images) > 0:
        target_file = images[0]

    if not target_file:
        raise HTTPException(
            status_code=400,
            detail="No image file provided in request. Please upload a file."
        )

    original_filename = target_file.filename or "image.jpg"
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: JPG, JPEG, PNG, WEBP."
        )

    # Generate unique immutable inspection ID
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    inspection_id = inspection_id_param or f"INS-{timestamp_str}-{unique_suffix}"

    # Prepare persistent directories
    insp_folder = INSPECTIONS_DIR / inspection_id
    images_folder = insp_folder / "images"
    ocr_folder = insp_folder / "ocr"
    norm_folder = insp_folder / "normalized"
    comp_folder = insp_folder / "compliance"

    images_folder.mkdir(parents=True, exist_ok=True)
    ocr_folder.mkdir(parents=True, exist_ok=True)
    norm_folder.mkdir(parents=True, exist_ok=True)
    comp_folder.mkdir(parents=True, exist_ok=True)

    # Save uploaded image file by streaming in chunks to prevent large memory buffers
    saved_filename = f"product{ext}"
    saved_image_path = images_folder / saved_filename

    try:
        with open(saved_image_path, "wb") as f:
            while chunk := await target_file.read(64 * 1024):
                f.write(chunk)
        if saved_image_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save uploaded image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Execute RapidOCR inference with memory protection and concurrency serialization
    created_at_iso = datetime.now(timezone.utc).isoformat()
    
    async with ocr_lock:
        rss_start = get_current_rss_mb()
        logger.info(f"Acquired OCR lock for {inspection_id} (Process RSS: {rss_start:.1f} MB)...")
        
        # Preprocess image: scale down to max 720px to protect memory buffers and accelerate inference
        scale_x, scale_y = 1.0, 1.0
        ocr_input: Any = str(saved_image_path)
        temp_proc_path: Optional[Path] = None

        try:
            with Image.open(saved_image_path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img) or pil_img
                orig_w, orig_h = pil_img.size
                MAX_OCR_DIM = 720
                if max(orig_w, orig_h) > MAX_OCR_DIM:
                    scale = MAX_OCR_DIM / max(orig_w, orig_h)
                    new_w, new_h = max(1, int(orig_w * scale)), max(1, int(orig_h * scale))
                    resized = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
                    scale_x = orig_w / new_w
                    scale_y = orig_h / new_h
                    ocr_input = np.array(resized.convert("RGB"))[:, :, ::-1]
                    del resized
                    logger.info(f"Downscaled image for OCR from {orig_w}x{orig_h} to {new_w}x{new_h} (Scale: {scale_x:.2f}, {scale_y:.2f})")
                else:
                    scale_x, scale_y = 1.0, 1.0
                    ocr_input = np.array(pil_img.convert("RGB"))[:, :, ::-1]
        except Exception as img_err:
            logger.warning(f"Could not load image as numpy for OCR: {img_err}. Using file path.")
            ocr_input = str(saved_image_path)
            scale_x, scale_y = 1.0, 1.0

        try:
            engine = await asyncio.to_thread(get_ocr_engine)
            logger.info(f"Running RapidOCR on image input (Inspection: {inspection_id})...")
            result, elapse_list = await asyncio.to_thread(engine, ocr_input)

            ocr_regions = []
            if result:
                for idx, item in enumerate(result):
                    try:
                        # item format: [box_points, text, score]
                        pts = item[0]
                        txt = str(item[1]).strip()
                        score = float(item[2])
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        raw_bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
                        bbox_coords = [
                            int(raw_bbox[0] * scale_x),
                            int(raw_bbox[1] * scale_y),
                            int(raw_bbox[2] * scale_x),
                            int(raw_bbox[3] * scale_y)
                        ]
                    except Exception:
                        bbox_coords = [0, 0, 100, 50]
                        txt = str(item[1]) if len(item) > 1 else ""
                        score = float(item[2]) if len(item) > 2 else 0.8

                    ocr_regions.append({
                        "id": f"ocr_{idx + 1:03d}",
                        "text": txt,
                        "confidence": round(score, 4),
                        "bbox": bbox_coords,
                        "image_id": "IMG-001"
                    })

                del result

            logger.info(f"RapidOCR detected {len(ocr_regions)} text regions.")

        except (MemoryError, RuntimeError) as oom_err:
            logger.error(f"OCR memory/runtime constraint error: {oom_err}", exc_info=True)
            gc.collect()
            raise HTTPException(
                status_code=503,
                detail="The OCR engine encountered a memory constraint processing this image. Please try a smaller or pre-cropped image."
            )
        except Exception as e:
            logger.error(f"RapidOCR inference failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"OCR engine failed during image processing: {str(e)}"
            )
        finally:
            if temp_proc_path and temp_proc_path.exists():
                try:
                    temp_proc_path.unlink()
                except Exception:
                    pass
            ocr_input = None
            gc.collect()
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                libc.malloc_trim(0)
            except Exception:
                pass
            rss_end = get_current_rss_mb()
            logger.info(f"Released OCR inference resources for {inspection_id}. Process RSS: {rss_end:.1f} MB (Delta: {rss_end - rss_start:+.1f} MB).")

    # Build raw OCR response
    raw_ocr_response = {
        "inspection_id": inspection_id,
        "image": saved_filename,
        "engine": "RapidOCR",
        "created_at": created_at_iso,
        "ocr": ocr_regions
    }

    # Save raw OCR evidence (raw_ocr.json and result.json)
    for fname in ["raw_ocr.json", "result.json"]:
        with open(ocr_folder / fname, "w", encoding="utf-8") as f:
            json.dump(raw_ocr_response, f, ensure_ascii=False, indent=2)

    # Derive clean default product name from filename or explicit param
    initial_name = inspection_name_param.strip() if inspection_name_param and inspection_name_param.strip() else clean_filename_title(original_filename)

    # Save metadata.json
    metadata = {
        "inspection_id": inspection_id,
        "display_name": inspection_name_param.strip() if inspection_name_param and inspection_name_param.strip() else None,
        "product_name": initial_name,
        "created_at": created_at_iso,
        "original_filename": original_filename,
        "status": "ocr_completed",
        "region_count": len(ocr_regions),
        "is_custom_name": bool(inspection_name_param and inspection_name_param.strip())
    }
    with open(insp_folder / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return JSONResponse(content=raw_ocr_response)


# ====================================================================
# 2. NVIDIA Nemotron Semantic Normalization (POST /api/normalize)
# ====================================================================

@app.post("/api/normalize")
def normalize_inspection(payload: Dict[str, Any] = Body(...)):
    """
    POST /api/normalize
    Accepts { "inspection_id": "...", "ocr": [...] }
    1. Validates OCR input.
    2. Sends OCR observations to NVIDIA Nemotron 3 Ultra 550B-A55B.
    3. Validates structured output schema.
    4. Saves to `normalized/product_data.json`.
    5. Returns StructuredProductData JSON.
    """
    inspection_id = payload.get("inspection_id")
    if not inspection_id:
        raise HTTPException(status_code=400, detail="inspection_id is required.")

    insp_folder = INSPECTIONS_DIR / inspection_id
    if not insp_folder.exists():
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")

    ocr_regions_raw = payload.get("ocr")
    if not ocr_regions_raw:
        ocr_file = insp_folder / "ocr" / "raw_ocr.json"
        if not ocr_file.exists():
            ocr_file = insp_folder / "ocr" / "result.json"

        if not ocr_file.exists():
            raise HTTPException(status_code=400, detail="No OCR data provided and raw_ocr.json not found.")

        with open(ocr_file, "r", encoding="utf-8") as f:
            raw_ocr = json.load(f)
            ocr_regions_raw = raw_ocr.get("ocr", [])

    # Validate regions into OCRRegion objects
    ocr_tokens: List[OCRRegion] = []
    for r in ocr_regions_raw:
        try:
            ocr_tokens.append(OCRRegion.model_validate(r))
        except Exception as e:
            logger.warning(f"Skipping malformed OCR token {r}: {e}")

    # Run Nemotron Semantic Normalization
    try:
        structured_data = normalize_ocr_with_nemotron(ocr_tokens, inspection_id)
    except Exception as e:
        logger.error(f"Normalization failed for inspection {inspection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Normalization engine failed: {str(e)}")

    # Save to normalized/product_data.json
    norm_folder = insp_folder / "normalized"
    norm_folder.mkdir(parents=True, exist_ok=True)
    with open(norm_folder / "product_data.json", "w", encoding="utf-8") as f:
        json.dump(structured_data.model_dump(), f, ensure_ascii=False, indent=2)

    # Update metadata.json with extracted commodity_name if present and not custom renamed
    meta_file = insp_folder / "metadata.json"
    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["status"] = "normalized"
        meta["normalized_at"] = datetime.now(timezone.utc).isoformat()

        # Update product_name using composite formatting (<Commodity> — <Brand/Mfg>)
        extracted_name = structured_data.product.commodity_name.value if structured_data.product.commodity_name.status == "extracted" else None
        extracted_mfg = structured_data.product.manufacturer.value if structured_data.product.manufacturer.status == "extracted" else None
        composite_name = format_composite_product_title(extracted_name, extracted_mfg, meta.get("original_filename", ""))
        if composite_name and composite_name != "Untitled Inspection":
            meta["product_name"] = composite_name

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    return JSONResponse(content=structured_data.model_dump())


# ====================================================================
# 3. Phase 3: Legal Metrology Compliance Engine (POST /api/compliance)
# ====================================================================

@app.post("/api/compliance")
def evaluate_compliance_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    POST /api/compliance
    Accepts { "inspection_id": "...", "inspection_date": "...", "hints": {...} }
    1. Loads `normalized/product_data.json`.
    2. Runs deterministic Legal Metrology compliance evaluation against versioned rules.
    3. Saves `compliance/compliance_result.json`.
    4. Returns ComplianceResult JSON.
    """
    inspection_id = payload.get("inspection_id")
    if not inspection_id:
        raise HTTPException(status_code=400, detail="inspection_id is required.")

    insp_folder = INSPECTIONS_DIR / inspection_id
    if not insp_folder.exists():
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")

    inspection_date = payload.get("inspection_date")
    hints = payload.get("hints")

    try:
        compliance_result = run_compliance_evaluation(
            inspection_id=inspection_id,
            inspection_date=inspection_date,
            inspection_hints=hints
        )
        return JSONResponse(content=compliance_result.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Compliance evaluation failed for inspection {inspection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Compliance evaluation error: {str(e)}")


# ====================================================================
# 4. History Item Renaming Endpoint (PATCH /api/inspections/{id})
# ====================================================================

@app.patch("/api/inspections/{inspection_id}")
def rename_inspection(inspection_id: str, payload: RenameInspectionPayload):
    """
    PATCH /api/inspections/{inspection_id}
    Updates human-readable display_name metadata without altering inspection_id or filesystem paths.
    If display_name is empty/null/whitespace, resets custom name to fall back to automatic naming.
    """
    insp_dir = INSPECTIONS_DIR / inspection_id
    if not insp_dir.exists():
        raise HTTPException(status_code=404, detail="Inspection record not found")

    meta_file = insp_dir / "metadata.json"
    metadata = {
        "inspection_id": inspection_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "normalized"
    }
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    new_name = payload.display_name.strip() if payload.display_name else ""
    if new_name and new_name.lower() != "reset":
        metadata["display_name"] = new_name
        metadata["is_custom_name"] = True
    else:
        # Reset custom name so automatic naming priority takes over
        metadata["display_name"] = None
        metadata["is_custom_name"] = False

    metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"Inspection {inspection_id} display name updated to: '{metadata.get('display_name')}' (Auto resolved: '{resolve_display_name(metadata)}')")
    return metadata


# ====================================================================
# 5. Retrieval Endpoints
# ====================================================================

@app.get("/api/inspections")
def list_saved_inspections():
    """
    List all persistent inspections from backend disk with resolved human-readable titles
    """
    inspections = []
    for insp_dir in sorted(INSPECTIONS_DIR.glob("INS-*"), key=os.path.getmtime, reverse=True):
        if insp_dir.is_dir():
            meta_file = insp_dir / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        inspections.append(meta)
                except Exception:
                    continue
    return inspections


@app.get("/api/inspections/{inspection_id}")
def get_inspection_record(inspection_id: str):
    """
    Get complete inspection bundle (metadata, raw OCR, normalized product data, compliance report)
    """
    insp_dir = INSPECTIONS_DIR / inspection_id
    if not insp_dir.exists():
        raise HTTPException(status_code=404, detail="Inspection record not found")

    meta_file = insp_dir / "metadata.json"
    ocr_file = insp_dir / "ocr" / "raw_ocr.json"
    if not ocr_file.exists():
        ocr_file = insp_dir / "ocr" / "result.json"

    norm_file = insp_dir / "normalized" / "product_data.json"
    comp_file = insp_dir / "compliance" / "compliance_result.json"
    if not comp_file.exists():
        comp_file = insp_dir / "compliance" / "result.json"

    metadata = {}
    ocr_data = None
    normalized_data = None
    compliance_data = None

    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    if ocr_file.exists():
        try:
            with open(ocr_file, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except Exception:
            pass

    if norm_file.exists():
        try:
            with open(norm_file, "r", encoding="utf-8") as f:
                normalized_data = json.load(f)
        except Exception:
            pass

    if comp_file.exists():
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                compliance_data = json.load(f)
        except Exception:
            pass

    return {
        "metadata": metadata,
        "ocr": ocr_data,
        "normalized": normalized_data,
        "compliance": compliance_data
    }


@app.get("/api/inspections/{inspection_id}/ocr")
def get_inspection_ocr_endpoint(inspection_id: str):
    ocr_file = INSPECTIONS_DIR / inspection_id / "ocr" / "raw_ocr.json"
    if not ocr_file.exists():
        ocr_file = INSPECTIONS_DIR / inspection_id / "ocr" / "result.json"
    if not ocr_file.exists():
        raise HTTPException(status_code=404, detail="Raw OCR record not found")
    with open(ocr_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/inspections/{inspection_id}/normalized")
def get_inspection_normalized_endpoint(inspection_id: str):
    norm_file = INSPECTIONS_DIR / inspection_id / "normalized" / "product_data.json"
    if not norm_file.exists():
        raise HTTPException(status_code=404, detail="Normalized product data not found")
    with open(norm_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/inspections/{inspection_id}/compliance")
def get_inspection_compliance_endpoint(inspection_id: str):
    comp_file = INSPECTIONS_DIR / inspection_id / "compliance" / "compliance_result.json"
    if not comp_file.exists():
        comp_file = INSPECTIONS_DIR / inspection_id / "compliance" / "result.json"
    if not comp_file.exists():
        raise HTTPException(status_code=404, detail="Compliance evaluation record not found")
    with open(comp_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/inspections/{inspection_id}/image/{filename}")
def get_inspection_image(inspection_id: str, filename: str):
    """
    Serve saved commodity image for inspection
    """
    img_path = INSPECTIONS_DIR / inspection_id / "images" / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(img_path))


# ====================================================================
# 4. Phase 4: Inspection Summary & PDF Report Endpoints
# ====================================================================

@app.get("/api/inspections/{inspection_id}/summary")
def get_inspection_summary_endpoint(inspection_id: str):
    """
    GET /api/inspections/{inspection_id}/summary
    Generates or retrieves executive summary for the inspection.
    """
    insp_folder = INSPECTIONS_DIR / inspection_id
    if not insp_folder.exists():
        raise HTTPException(status_code=404, detail="Inspection record not found")

    # Load metadata
    meta = {}
    meta_file = insp_folder / "metadata.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    # Load product data
    product_data = None
    norm_file = insp_folder / "normalized" / "product_data.json"
    if norm_file.exists():
        try:
            with open(norm_file, "r", encoding="utf-8") as f:
                product_data = StructuredProductData.model_validate_json(f.read())
        except Exception:
            pass

    # Load or run compliance
    comp_file = insp_folder / "compliance" / "compliance_result.json"
    if comp_file.exists():
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                compliance = ComplianceResult.model_validate_json(f.read())
        except Exception:
            compliance = run_compliance_evaluation(inspection_id)
    else:
        compliance = run_compliance_evaluation(inspection_id)

    display_title = meta.get("display_name") or meta.get("product_name") or "Packaged Commodity"
    summary_text, source = generate_inspection_summary(compliance, product_data, display_title)

    return {
        "inspection_id": inspection_id,
        "summary": summary_text,
        "source": source,
        "overall_status": compliance.overall_status
    }


@app.post("/api/inspections/{inspection_id}/report")
@app.get("/api/inspections/{inspection_id}/report")
def export_inspection_pdf_endpoint(inspection_id: str):
    """
    POST/GET /api/inspections/{inspection_id}/report
    Generates and returns professional Legal Metrology PDF inspection report.
    """
    insp_folder = INSPECTIONS_DIR / inspection_id
    if not insp_folder.exists():
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")

    try:
        pdf_bytes = generate_inspection_pdf(inspection_id)
    except Exception as e:
        logger.error(f"PDF generation failed for inspection {inspection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"PDF report generation failed: {str(e)}")

    pdf_file_path = insp_folder / "report" / "inspection_report.pdf"

    # Derive dynamic download filename from inspection display name
    meta_file = insp_folder / "metadata.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    display_title = resolve_display_name(meta)
    from backend.services.report_service import generate_pdf_filename
    download_filename = generate_pdf_filename(display_title, inspection_id)

    return FileResponse(
        path=str(pdf_file_path),
        media_type="application/pdf",
        filename=download_filename,
        headers={
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
