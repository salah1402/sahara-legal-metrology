import { getApiConfig, ApiError } from './api';
import type { OCRResponse, BackendOCRResponse } from '../types/ocr';
import type { StructuredInstruction } from '../types/instruction';

/**
 * Service to interface with PaddleOCR backend
 * Target endpoint: POST http://127.0.0.1:8000/api/ocr (multipart/form-data)
 */

export interface OCRRequestOptions {
  inspectionId?: string;
  files: (File | Blob)[];
  imageIds?: string[];
  structuredInstruction?: StructuredInstruction;
}

/**
 * Process a single image file through the real FastAPI PaddleOCR backend
 */
export async function processOCR(file: File | Blob, inspectionId?: string): Promise<BackendOCRResponse> {
  const config = getApiConfig();
  const formData = new FormData();

  const filename = file instanceof File ? file.name : `label_capture_${Date.now()}.jpg`;
  formData.append('file', file, filename);

  if (inspectionId) {
    formData.append('inspection_id_param', inspectionId);
  }

  const endpoint = `${config.baseUrl.replace(/\/+$/, '')}/api/ocr`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
      // IMPORTANT: Do NOT manually set Content-Type header so browser sets multipart boundary automatically
    });

    if (!response.ok) {
      let errDetail = response.statusText;
      try {
        const errJson = await response.json();
        if (errJson?.detail) errDetail = errJson.detail;
      } catch {
        // ignore
      }
      throw new ApiError(
        errDetail || `OCR request failed with status ${response.status}`,
        response.status,
        'OCR_HTTP_ERROR'
      );
    }

    const data: BackendOCRResponse = await response.json();
    return data;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      'Unable to connect to the OCR backend. Make sure the FastAPI service is running on http://127.0.0.1:8000.',
      0,
      'BACKEND_UNAVAILABLE'
    );
  }
}

/**
 * Perform OCR for multiple or single images (maps to processOCR)
 */
export async function performOCR(options: OCRRequestOptions): Promise<OCRResponse> {
  if (!options.files || options.files.length === 0) {
    throw new ApiError('No image files provided for OCR processing', 400, 'NO_FILES');
  }

  const primaryFile = options.files[0];
  const backendResult = await processOCR(primaryFile, options.inspectionId);

  // Normalize into frontend multi-image OCR structure
  return {
    inspection_id: backendResult.inspection_id,
    engine: backendResult.engine || 'PaddleOCR',
    images: [
      {
        image_id: options.imageIds?.[0] || 'img_001',
        ocr: backendResult.ocr || []
      }
    ]
  };
}

/**
 * Fetch raw OCR record for an existing inspection
 * Target endpoint: GET /api/inspections/:id
 */
export async function getInspectionOCR(inspectionId: string): Promise<OCRResponse | null> {
  const config = getApiConfig();

  try {
    const url = `${config.baseUrl.replace(/\/+$/, '')}/inspections/${inspectionId}`;
    const response = await fetch(url);
    if (response.ok) {
      const data = await response.json();
      if (data?.ocr) {
        return {
          inspection_id: data.ocr.inspection_id || inspectionId,
          engine: data.ocr.engine || 'PaddleOCR',
          images: [
            {
              image_id: 'img_001',
              ocr: data.ocr.ocr || []
            }
          ]
        };
      }
    }
  } catch {
    // ignore
  }

  // Check saved inspections in localStorage
  try {
    const savedJson = localStorage.getItem(`sahara_insp_${inspectionId}`);
    if (savedJson) {
      const parsed = JSON.parse(savedJson);
      return parsed.ocrResult || null;
    }
  } catch {
    // ignore
  }

  return null;
}
