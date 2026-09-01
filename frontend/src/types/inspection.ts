import type { OCRResponse } from './ocr';
import type { StructuredInstruction } from './instruction';
import type { StructuredProductData } from './normalized';
import type { ComplianceResult } from './compliance';

export type InspectionStatus =
  | 'New'
  | 'OCR Processing'
  | 'OCR Complete'
  | 'Understanding Label'
  | 'Evaluating Compliance'
  | 'Structured Data Ready'
  | 'Compliant'
  | 'Non-Compliant'
  | 'Needs Review'
  | 'Under Review';

export interface InspectionImage {
  id: string;
  name: string;
  size: number;
  type: string;
  previewUrl: string;
  base64?: string;
  width?: number;
  height?: number;
  uploadedAt: string;
}

export interface InspectionMetadata {
  inspection_id: string;
  display_name?: string;
  created_at: string;
  updated_at?: string;
  product_name?: string;
  brand_name?: string;
  category?: string;
  declared_mrp?: string;
  declared_quantity?: string;
  image_count: number;
  status: InspectionStatus;
  notes?: string;
  inspector_name?: string;
}

export interface LegalMetrologyRuleCheck {
  rule_id: string;
  rule_name: string;
  regulation_ref: string;
  description: string;
  status: 'pending' | 'satisfied' | 'violation' | 'unverified';
  detected_text?: string;
  evidence_region_id?: string;
  notes?: string;
}

export interface InspectionRecord {
  id: string;
  metadata: InspectionMetadata;
  instructionPrompt?: string;
  structuredInstruction?: StructuredInstruction;
  images: InspectionImage[];
  ocrResult?: OCRResponse;
  normalized?: StructuredProductData;
  compliance?: ComplianceResult;
  ruleChecks?: LegalMetrologyRuleCheck[];
}

export type InspectionPipelineStage =
  | 'idle'
  | 'preparing_image'
  | 'processing_ocr'
  | 'understanding_label'
  | 'evaluating_compliance'
  | 'complete'
  | 'error';
