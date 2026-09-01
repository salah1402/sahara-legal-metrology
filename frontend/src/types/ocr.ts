/**
 * OCR Data Types for PaddleOCR backend integration
 * Coordinates format: [x1, y1, x2, y2] (top-left to bottom-right)
 */

export interface OCRTextRegion {
  id: string;
  text: string;
  confidence: number; // 0.0 to 1.0
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  fieldCategory?: 
    | 'mrp'
    | 'net_quantity'
    | 'mfg_date'
    | 'expiry_date'
    | 'manufacturer'
    | 'packer'
    | 'country_of_origin'
    | 'consumer_care'
    | 'generic_name'
    | 'ingredient_list'
    | 'fssai_lic'
    | 'unclassified';
}

export type OCRRegion = OCRTextRegion;

export interface BackendOCRResponse {
  inspection_id: string;
  image: string;
  engine: string;
  created_at: string;
  ocr: OCRTextRegion[];
  processing_time_ms?: number;
}

export interface ImageOCR {
  image_id: string;
  ocr: OCRTextRegion[];
  dimensions?: {
    width: number;
    height: number;
  };
}

export interface OCRResponse {
  inspection_id: string;
  images: ImageOCR[];
  engine?: string;
  processing_time_ms?: number;
}
