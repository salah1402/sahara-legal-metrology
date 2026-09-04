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
  const base = config.baseUrl.replace(/\/+$/, '');
  const response = await fetch(`${base}/api/inspections/${inspectionId}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to fetch inspection summary: ${response.statusText}`);
  }
  return response.json();
}

export const getInspectionSummary = fetchInspectionSummary;

export async function exportInspectionPDF(inspectionId: string): Promise<Blob> {
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/+$/, '');
  const response = await fetch(`${base}/api/inspections/${inspectionId}/report`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`Failed to generate PDF inspection report: ${response.statusText}`);
  }
  return response.blob();
}

export function generatePdfFilename(inspectionName: string | undefined | null, inspectionId: string): string {
  if (!inspectionName || !inspectionName.trim()) {
    return `SAHARA_Inspection_${inspectionId}.pdf`;
  }
  const cleanName = inspectionName.trim();
  if (cleanName.toLowerCase() === 'untitled inspection' || cleanName.toLowerCase() === 'untitled' || cleanName.toLowerCase() === 'packaged commodity') {
    return `SAHARA_Inspection_${inspectionId}.pdf`;
  }

  const sanitized = cleanName
    .replace(/[—–\-]/g, '_')
    .replace(/[\\/*?:"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .replace(/[^\w_]/g, '')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');

  if (!sanitized) {
    return `SAHARA_Inspection_${inspectionId}.pdf`;
  }

  return `SAHARA_${sanitized}_Inspection_Report.pdf`;
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
