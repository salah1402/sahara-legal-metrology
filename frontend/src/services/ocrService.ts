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
async function pingBackend(baseUrl: string): Promise<boolean> {
  const cleanBase = baseUrl.replace(/\/+$/, '');
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${cleanBase}/health`, {
      method: 'GET',
      mode: 'cors',
      signal: controller.signal,
    });
    clearTimeout(timer);
    return res.ok;
  } catch {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const resRoot = await fetch(`${cleanBase}/`, {
        method: 'GET',
        mode: 'cors',
        signal: controller.signal,
      });
      clearTimeout(timer);
      return resRoot.ok;
    } catch {
      return false;
    }
  }
}

/**
 * Process a single image file through the real FastAPI RapidOCR backend
 */
export async function processOCR(
  file: File | Blob,
  inspectionId?: string,
  onProgress?: (statusMessage: string) => void
): Promise<BackendOCRResponse> {
  const config = getApiConfig();
  const formData = new FormData();

  const filename = file instanceof File ? file.name : `label_capture_${Date.now()}.jpg`;
  formData.append('file', file, filename);

  if (inspectionId) {
    formData.append('inspection_id_param', inspectionId);
  }

  const endpoint = `${config.baseUrl.replace(/\/+$/, '')}/api/ocr`;

  // Allow a primary attempt. If a cold-start response (502/503) or connection drop occurs,
  // we poll GET / until Render wakes up (up to 36 seconds), then retry the request.
  const maxAttempts = 2;
  let lastError: any = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeoutMs || 180000);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // If backend returns 502/503 (Render cold boot gateway status)
      if ((response.status === 502 || response.status === 503) && attempt < maxAttempts) {
        console.warn(`Backend returned HTTP ${response.status} during boot. Starting cold-start wake-up wait...`);
        lastError = new Error(`HTTP ${response.status} Bad Gateway during cold start`);
      } else if (!response.ok) {
        // Real HTTP errors from the backend application (400, 422, 413, 500, etc.)
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
      } else {
        const data: BackendOCRResponse = await response.json();
        return data;
      }
    } catch (err: any) {
      clearTimeout(timeoutId);
      lastError = err;

      // Do not catch or retry real application ApiErrors (400, 422, etc.)
      if (err instanceof ApiError) {
        throw err;
      }

      console.warn(`Attempt ${attempt} failed with network/cold-start error:`, err?.message || err);
    }

    // If attempt 1 failed due to cold boot or network drop, poll backend until online
    if (attempt === 1) {
      onProgress?.('Waking inspection service… Please wait.');
      console.log('Suspected cloud cold-start. Polling backend /health until service is online...');

      const maxPollCycles = 12; // 12 * 3s = 36s max
      let isOnline = false;

      for (let cycle = 1; cycle <= maxPollCycles; cycle++) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        onProgress?.('Waking inspection service… Please wait.');

        const healthy = await pingBackend(config.baseUrl);
        if (healthy) {
          console.log(`Backend is online after ${cycle * 3}s. Retrying OCR request...`);
          onProgress?.('Inspection service online! Running RapidOCR detection...');
          isOnline = true;
          break;
        }
      }

      if (!isOnline) {
        console.warn('Backend wake-up polling reached timeout (36s). Attempting final submission...');
      }
    }
  }

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
