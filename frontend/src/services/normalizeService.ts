import { getApiConfig, ApiError } from './api';
import type { StructuredProductData } from '../types/normalized';
import type { OCRTextRegion } from '../types/ocr';

/**
 * Service to interface with NVIDIA Nemotron Semantic Normalization endpoint
 * Target endpoint: POST http://127.0.0.1:8000/api/normalize
 */
export async function normalizeOCR(
  inspectionId: string,
  ocrTokens?: OCRTextRegion[]
): Promise<StructuredProductData> {
  const config = getApiConfig();
  const endpoint = `${config.baseUrl.replace(/\/+$/, '')}/api/normalize`;

  try {
    const payload: { inspection_id: string; ocr?: OCRTextRegion[] } = {
      inspection_id: inspectionId,
    };
    if (ocrTokens && ocrTokens.length > 0) {
      payload.ocr = ocrTokens;
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
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
        errDetail || `Normalization failed with status ${response.status}`,
        response.status,
        'NORMALIZE_HTTP_ERROR'
      );
    }

    const data: StructuredProductData = await response.json();
    return data;
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      'Unable to connect to Normalization backend service.',
      0,
      'BACKEND_UNAVAILABLE'
    );
  }
}
