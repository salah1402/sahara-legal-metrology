import { getApiConfig, ApiError } from './api';
import type { OCRResponse, BackendOCRResponse } from '../types/ocr';
import type { StructuredInstruction } from '../types/instruction';

/**
 * Service to interface with RapidOCR backend
 * Target endpoint: POST /api/ocr (multipart/form-data)
 */

export interface OCRRequestOptions {
  inspectionId?: string;
  files: (File | Blob)[];
  imageIds?: string[];
  structuredInstruction?: StructuredInstruction;
}

/**
 * Process a single image file through the real FastAPI RapidOCR backend
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

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), config.timeoutMs || 180000);

  // Allow up to 2 attempts in case the cloud backend (Render) is cold-starting (502/503)
  const maxAttempts = 2;
  let lastError: any = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      if (attempt > 1) {
        // Wait 3s before retrying cold start
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        // IMPORTANT: Do NOT manually set Content-Type header so browser sets multipart boundary automatically
      });

      // If backend returns 502/503 during cold boot, retry once
      if ((response.status === 502 || response.status === 503) && attempt < maxAttempts) {
        console.warn(`Backend returned HTTP ${response.status} during boot. Retrying OCR request...`);
        continue;
      }

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
      clearTimeout(timeoutId);
      return data;
    } catch (err: any) {
      lastError = err;
      if (err instanceof ApiError) {
        clearTimeout(timeoutId);
        throw err;
      }
      if (attempt >= maxAttempts) {
        break;
      }
    }
  }

  clearTimeout(timeoutId);

  const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const errorMsg = isLocal
    ? 'Unable to connect to the local development OCR backend. Make sure your local FastAPI service is running.'
    : `Unable to connect to the SAHARA inspection backend (${config.baseUrl}). The service may be waking up from cold start; please wait a moment and try again.`;

  throw new ApiError(errorMsg, 0, 'BACKEND_UNAVAILABLE', lastError);
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
    engine: backendResult.engine || 'RapidOCR',
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
    const url = `${config.baseUrl.replace(/\/+$/, '')}/api/inspections/${inspectionId}`;
    const response = await fetch(url);
    if (response.ok) {
      const data = await response.json();
      if (data?.ocr) {
        return {
          inspection_id: data.ocr.inspection_id || inspectionId,
          engine: data.ocr.engine || 'RapidOCR',
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
