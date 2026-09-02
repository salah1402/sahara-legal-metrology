import { getApiConfig } from './api';
import type { ComplianceResult } from '../types/compliance';

/**
 * Trigger Phase 3 Legal Metrology Compliance Engine on backend
 * Target: POST /api/compliance
 */
export async function evaluateCompliance(
  inspectionId: string,
  inspectionDate?: string
): Promise<ComplianceResult> {
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/+$/, '');

  const response = await fetch(`${base}/api/compliance`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      inspection_id: inspectionId,
      inspection_date: inspectionDate,
    }),
  });

  if (!response.ok) {
    let errorDetail = `Failed to evaluate compliance (${response.status})`;
    try {
      const err = await response.json();
      if (err.detail) errorDetail = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  const result: ComplianceResult = await response.json();
  return result;
}

/**
 * Fetch saved compliance report for an inspection
 * Target: GET /api/inspections/:id/compliance
 */
export async function getInspectionCompliance(inspectionId: string): Promise<ComplianceResult | null> {
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/+$/, '');

  try {
    const response = await fetch(`${base}/api/inspections/${inspectionId}/compliance`);
    if (response.ok) {
      return await response.json();
    }
  } catch (err) {
    console.warn(`Could not fetch compliance report for ${inspectionId}:`, err);
  }
  return null;
}
