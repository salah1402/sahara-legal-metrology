import os
import json
import requests

print("=== EXECUTING METRACHECK REAL-WORLD VERIFICATION ===")
img_file = "ocr test/img/images.png"
assert os.path.exists(img_file), f"Image file {img_file} not found"

# 1. OCR Ingestion
r1 = requests.post(
    "http://127.0.0.1:8000/api/ocr",
    files={"file": ("britannia_sample.png", open(img_file, "rb"), "image/png")}
)
assert r1.status_code == 200, f"OCR failed: {r1.text}"
ocr_data = r1.json()
insp_id = ocr_data["inspection_id"]
regions_len = len(ocr_data["ocr"])
print(f"1. PaddleOCR Success -> Inspection ID: {insp_id}, Regions: {regions_len}")

# 2. Nemotron Semantic Normalization
r2 = requests.post(
    "http://127.0.0.1:8000/api/normalize",
    json={"inspection_id": insp_id, "ocr": ocr_data["ocr"]}
)
assert r2.status_code == 200, f"Normalize failed: {r2.text}"
norm_data = r2.json()
print("2. Nemotron Normalization Success -> Schema:", norm_data.get("schema_version"), "Coverage:", [img.get("image_type") for img in norm_data.get("images", [])])

# 3. Rename Inspection (PATCH /api/inspections/{id})
r3 = requests.patch(
    f"http://127.0.0.1:8000/api/inspections/{insp_id}",
    json={"display_name": "Britannia Good Day — Front & Back Panel"}
)
assert r3.status_code == 200, f"Rename failed: {r3.text}"
renamed_meta = r3.json()
print("3. Rename API Success -> Display Name:", renamed_meta.get("display_name"), "ID:", renamed_meta.get("inspection_id"))
assert renamed_meta.get("inspection_id") == insp_id, "Inspection ID changed!"

# 4. Retrieval Bundle
r4 = requests.get(f"http://127.0.0.1:8000/api/inspections/{insp_id}")
assert r4.status_code == 200, f"Bundle fetch failed: {r4.text}"
bundle = r4.json()
print("4. Retrieval Bundle Verified -> Has raw OCR:", bool(bundle.get("ocr")), "Has Normalized:", bool(bundle.get("normalized")), "Display Title:", bundle.get("metadata", {}).get("display_name"))

# 5. Disk Persistence Verification
for f in ["images/product.png", "ocr/raw_ocr.json", "normalized/product_data.json", "metadata.json"]:
    p = os.path.join("backend", "inspections", insp_id, f)
    assert os.path.exists(p), f"Missing persistent file {p}"
print("5. All Persistent Storage Files Verified on Disk!")
print("=== METRACHECK PHASE 2 FINALIZATION COMPLETE & VERIFIED ===")
