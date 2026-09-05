import { getApiConfig, ApiError } from './api';
import type { StructuredProductData } from '../types/normalized';
import type { OCRTextRegion } from '../types/ocr';

/**
 * Service to interface with NVIDIA Nemotron Semantic Normalization endpoint
 * Target endpoint: POST /api/normalize
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
    const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    const msg = isLocal
      ? 'Unable to connect to local development Normalization service. Make sure your local backend is running.'
      : `Unable to connect to Normalization backend service (${config.baseUrl}).`;
    throw new ApiError(
      msg,
      0,
      'BACKEND_UNAVAILABLE'
    );
  }
}
