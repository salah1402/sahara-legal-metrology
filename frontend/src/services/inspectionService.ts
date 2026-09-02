import type { InspectionRecord, InspectionMetadata } from '../types/inspection';
import { SAMPLE_INSPECTIONS } from './fixtures';
import { getApiConfig } from './api';

const STORAGE_KEY_LIST = 'sahara_inspections_list';
const STORAGE_PREFIX = 'sahara_insp_';

function initStorage(): void {
  try {
    const list = localStorage.getItem(STORAGE_KEY_LIST);
    if (!list) {
      const initialMetas: InspectionMetadata[] = SAMPLE_INSPECTIONS.map(s => s.metadata);
      localStorage.setItem(STORAGE_KEY_LIST, JSON.stringify(initialMetas));
      SAMPLE_INSPECTIONS.forEach(s => {
        localStorage.setItem(`${STORAGE_PREFIX}${s.id}`, JSON.stringify(s));
      });
    }
  } catch (e) {
    console.error('Failed to initialize local inspection storage', e);
  }
}

function STORAGEPREFIX_KEY(id: string): string {
  return `${STORAGE_PREFIX}${id}`;
}

/**
 * List all persistent inspections metadata
 * Target: GET /api/inspections
 */
export async function listInspections(): Promise<InspectionMetadata[]> {
  initStorage();
  const config = getApiConfig();

  try {
    const response = await fetch(`${config.baseUrl.replace(/\/+$/, '')}/api/inspections`);
    if (response.ok) {
      const remoteList = await response.json();
      if (Array.isArray(remoteList) && remoteList.length > 0) {
        return remoteList;
      }
    }
  } catch {
    // fallback to local storage
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY_LIST);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // fallback
  }

  return SAMPLE_INSPECTIONS.map(s => s.metadata);
}

/**
 * Fetch complete inspection record by ID
 * Target: GET /api/inspections/:id
 */
export async function getInspection(id: string): Promise<InspectionRecord | null> {
  initStorage();
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/+$/, '');

  try {
    const response = await fetch(`${base}/api/inspections/${id}`);
    if (response.ok) {
      const data = await response.json();
      const record: InspectionRecord = {
        id: data.metadata?.inspection_id || id,
        metadata: data.metadata || {
          inspection_id: id,
          created_at: new Date().toISOString(),
          image_count: 1,
          status: 'Structured Data Ready'
        },
        images: [
          {
            id: 'img_001',
            name: data.ocr?.image || 'product.jpg',
            size: 0,
            type: 'image/jpeg',
            previewUrl: `${base}/api/inspections/${id}/image/${data.ocr?.image || 'product.jpg'}`,
            uploadedAt: data.metadata?.created_at || new Date().toISOString()
          }
        ],
        ocrResult: data.ocr ? {
          inspection_id: id,
          engine: data.ocr.engine || 'PaddleOCR',
          images: [
            {
              image_id: 'img_001',
              ocr: data.ocr.ocr || []
            }
          ]
        } : undefined,
        normalized: data.normalized || undefined,
        compliance: data.compliance || undefined
      };
      return record;
    }
  } catch {
    // fallback
  }

  try {
    const raw = localStorage.getItem(STORAGEPREFIX_KEY(id));
    if (raw) {
      return JSON.parse(raw);
    }
  } catch {
    // fallback
  }

  const fixture = SAMPLE_INSPECTIONS.find(s => s.id === id);
  return fixture || null;
}

/**
 * Rename inspection display_name
 * Target: PATCH /api/inspections/:id
 */
export async function renameInspection(id: string, displayName: string): Promise<InspectionMetadata> {
  initStorage();
  const config = getApiConfig();
  const trimmedName = displayName.trim();

  let updatedMeta: InspectionMetadata = {
    inspection_id: id,
    display_name: trimmedName,
    created_at: new Date().toISOString(),
    image_count: 1,
    status: 'Structured Data Ready',
    updated_at: new Date().toISOString()
  };

  try {
    const response = await fetch(`${config.baseUrl.replace(/\/+$/, '')}/api/inspections/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ display_name: trimmedName }),
    });

    if (response.ok) {
      updatedMeta = await response.json();
    }
  } catch (err) {
    console.warn('Backend rename unreachable, saving locally:', err);
  }

  // Update local storage record & metadata list
  try {
    const listRaw = localStorage.getItem(STORAGE_KEY_LIST);
    if (listRaw) {
      const list: InspectionMetadata[] = JSON.parse(listRaw);
      const idx = list.findIndex(item => item.inspection_id === id);
      if (idx >= 0) {
        list[idx].display_name = trimmedName;
        list[idx].updated_at = new Date().toISOString();
        updatedMeta = { ...list[idx] };
      }
      localStorage.setItem(STORAGE_KEY_LIST, JSON.stringify(list));
    }

    const recordRaw = localStorage.getItem(STORAGEPREFIX_KEY(id));
    if (recordRaw) {
      const rec: InspectionRecord = JSON.parse(recordRaw);
      rec.metadata.display_name = trimmedName;
      rec.metadata.updated_at = new Date().toISOString();
      localStorage.setItem(STORAGEPREFIX_KEY(id), JSON.stringify(rec));
    }
  } catch (e) {
    console.error('Failed to update local storage for renamed inspection', e);
  }

  return updatedMeta;
}

/**
 * Save / Update an inspection record
 */
export async function saveInspection(record: InspectionRecord): Promise<InspectionRecord> {
  initStorage();

  try {
    localStorage.setItem(STORAGEPREFIX_KEY(record.id), JSON.stringify(record));

    const listRaw = localStorage.getItem(STORAGE_KEY_LIST);
    let list: InspectionMetadata[] = listRaw ? JSON.parse(listRaw) : [];
    
    const existingIndex = list.findIndex(item => item.inspection_id === record.id);
    if (existingIndex >= 0) {
      list[existingIndex] = { ...record.metadata };
    } else {
      list.unshift({ ...record.metadata });
    }

    localStorage.setItem(STORAGE_KEY_LIST, JSON.stringify(list));
  } catch (e) {
    console.error('Error persisting inspection record', e);
  }

  return record;
}

/**
 * Delete inspection record
 */
export async function deleteInspection(id: string): Promise<void> {
  try {
    localStorage.removeItem(STORAGEPREFIX_KEY(id));
    const listRaw = localStorage.getItem(STORAGE_KEY_LIST);
    if (listRaw) {
      const list: InspectionMetadata[] = JSON.parse(listRaw);
      const filtered = list.filter(item => item.inspection_id !== id);
      localStorage.setItem(STORAGE_KEY_LIST, JSON.stringify(filtered));
    }
  } catch (e) {
    console.error('Failed to delete inspection', e);
  }
}
