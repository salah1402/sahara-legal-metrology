/**
 * Service to fetch inspection summaries and export PDF reports from SAHARA backend.
 */
import { getApiConfig } from './api';

export interface InspectionSummaryResponse {
  inspection_id: string;
  summary: string;
  source: 'nemotron' | 'deterministic_fallback';
  overall_status: string;
}

export async function fetchInspectionSummary(inspectionId: string): Promise<InspectionSummaryResponse> {
  const config = getApiConfig();
  const response = await fetch(`${config.baseUrl}/inspections/${inspectionId}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch inspection summary: ${response.statusText}`);
  }
  return response.json();
}

export const getInspectionSummary = fetchInspectionSummary;

export async function exportInspectionPDF(inspectionId: string): Promise<Blob> {
  const config = getApiConfig();
  const response = await fetch(`${config.baseUrl}/inspections/${inspectionId}/report`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to generate PDF inspection report: ${response.statusText}`);
  }
  return response.blob();
}

export function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
