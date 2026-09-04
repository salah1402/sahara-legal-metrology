from typing import List, Optional, Literal, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------
# OCR Input Schemas
# ---------------------------------------------------------

class OCRRegion(BaseModel):
    id: str = Field(..., description="Unique OCR token ID e.g. ocr_001")
    text: str = Field(..., description="Raw text extracted by RapidOCR")
    confidence: float = Field(..., description="RapidOCR recognition confidence 0.0 - 1.0")
    bbox: List[int] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    image_id: Optional[str] = Field("IMG-001", description="Source image identifier")


class RawOCRData(BaseModel):
    inspection_id: str
    image: str
    engine: str = "RapidOCR"
    created_at: str
    ocr: List[OCRRegion]


# ---------------------------------------------------------
# Evidence Tracking Schema
# ---------------------------------------------------------

class Evidence(BaseModel):
    image_id: str = "IMG-001"
    source_text: str
    ocr_confidence: float
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2]")


# ---------------------------------------------------------
# Image Coverage Classification
# ---------------------------------------------------------

ImageType = Literal[
    "front_panel",
    "back_panel",
    "side_panel",
    "nutrition_panel",
    "ingredients_panel",
    "mrp_panel",
    "manufacturer_panel",
    "importer_panel",
    "barcode_panel",
    "mixed_panel",
    "unknown"
]


class ImageCoverage(BaseModel):
    image_id: str = "IMG-001"
    image_type: ImageType = "unknown"
    visibility_confidence: float = 1.0
    visible_sections: List[str] = Field(default_factory=list)


# ---------------------------------------------------------
# Field Statuses & Value Containers
# ---------------------------------------------------------

FieldStatus = Literal[
    "extracted",
    "ambiguous",
    "conflicting",
    "not_observed",
    "unreadable"
]

T = TypeVar("T")


class CandidateValue(BaseModel):
    value: Any
    evidence: Evidence


class ExtractedField(BaseModel, Generic[T]):
    value: Optional[T] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    precision: Optional[str] = None
    status: FieldStatus = "not_observed"
    evidence: List[Evidence] = Field(default_factory=list)
    candidates: Optional[List[CandidateValue]] = None

    @model_validator(mode="before")
    @classmethod
    def wrap_raw_value(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            if data is None:
                return {"value": None, "status": "not_observed"}
            return {"value": data, "status": "extracted"}
        return data


# ---------------------------------------------------------
# Product Fields
# ---------------------------------------------------------

class ProductFields(BaseModel):
    commodity_name: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    manufacturer: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    packer: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    importer: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    manufacturer_address: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    packer_address: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    importer_address: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    country_of_origin: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    net_quantity: ExtractedField[float] = Field(default_factory=lambda: ExtractedField[float]())
    number_of_items: ExtractedField[int] = Field(default_factory=lambda: ExtractedField[int]())
    mrp: ExtractedField[float] = Field(default_factory=lambda: ExtractedField[float]())
    manufacturing_date: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    packing_date: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    expiry_date: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    best_before: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    consumer_care: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    consumer_care_phone: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())
    consumer_care_email: ExtractedField[str] = Field(default_factory=lambda: ExtractedField[str]())


class OtherDetectedInfoItem(BaseModel):
    category: str = "general"
    label: str
    value: str
    evidence: List[Evidence] = Field(default_factory=list)


class AmbiguityItem(BaseModel):
    field: str
    description: str
    evidence: List[Evidence] = Field(default_factory=list)


class ConflictItem(BaseModel):
    field: str
    description: str
    candidates: List[CandidateValue] = Field(default_factory=list)


# ---------------------------------------------------------
# Complete Structured Product Schema (Version 1.0)
# ---------------------------------------------------------

class StructuredProductData(BaseModel):
    schema_version: str = "1.0"
    inspection_id: str
    images: List[ImageCoverage] = Field(default_factory=list)
    product: ProductFields = Field(default_factory=ProductFields)
    other_detected_information: List[OtherDetectedInfoItem] = Field(default_factory=list)
    ambiguities: List[AmbiguityItem] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
