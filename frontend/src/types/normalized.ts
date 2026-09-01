export type FieldStatus =
  | 'extracted'
  | 'ambiguous'
  | 'conflicting'
  | 'not_observed'
  | 'unreadable';

export type ImageType =
  | 'front_panel'
  | 'back_panel'
  | 'side_panel'
  | 'nutrition_panel'
  | 'ingredients_panel'
  | 'mrp_panel'
  | 'manufacturer_panel'
  | 'importer_panel'
  | 'barcode_panel'
  | 'mixed_panel'
  | 'unknown';

export interface Evidence {
  image_id: string;
  source_text: string;
  ocr_confidence: number;
  bbox: [number, number, number, number];
}

export interface CandidateValue {
  value: any;
  evidence: Evidence;
}

export interface ImageCoverage {
  image_id: string;
  image_type: ImageType;
  visibility_confidence: number;
  visible_sections: string[];
}

export interface ExtractedField<T = any> {
  value?: T | null;
  unit?: string | null;
  currency?: string | null;
  precision?: string | null;
  status: FieldStatus;
  evidence: Evidence[];
  candidates?: CandidateValue[] | null;
}

export interface ProductFields {
  commodity_name: ExtractedField<string>;
  manufacturer: ExtractedField<string>;
  packer: ExtractedField<string>;
  importer: ExtractedField<string>;
  manufacturer_address: ExtractedField<string>;
  packer_address: ExtractedField<string>;
  importer_address: ExtractedField<string>;
  country_of_origin: ExtractedField<string>;
  net_quantity: ExtractedField<number>;
  number_of_items: ExtractedField<number>;
  mrp: ExtractedField<number>;
  manufacturing_date: ExtractedField<string>;
  packing_date: ExtractedField<string>;
  expiry_date: ExtractedField<string>;
  best_before: ExtractedField<string>;
  consumer_care: ExtractedField<string>;
  consumer_care_phone: ExtractedField<string>;
  consumer_care_email: ExtractedField<string>;
}

export interface OtherDetectedInfoItem {
  category: string;
  label: string;
  value: string;
  evidence: Evidence[];
}

export interface AmbiguityItem {
  field: string;
  description: string;
  evidence: Evidence[];
}

export interface ConflictItem {
  field: string;
  description: string;
  candidates: CandidateValue[];
}

export interface StructuredProductData {
  schema_version: string;
  inspection_id: string;
  images: ImageCoverage[];
  product: ProductFields;
  other_detected_information: OtherDetectedInfoItem[];
  ambiguities: AmbiguityItem[];
  conflicts: ConflictItem[];
}
