/**
 * Common formatting helpers for SAHARA — Legal Metrology Inspection System
 */

export function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return isoString;
  }
}

export function formatTimeAgo(isoString: string): string {
  try {
    const diffSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  } catch {
    return '';
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function normalizeBoundingBox(
  bbox: [number, number, number, number],
  imageWidth: number,
  imageHeight: number
) {
  if (!bbox || bbox.length < 4 || imageWidth <= 0 || imageHeight <= 0) {
    return { leftPercent: 0, topPercent: 0, widthPercent: 0, heightPercent: 0 };
  }
  const [x1, y1, x2, y2] = bbox;
  const leftPercent = Math.max(0, Math.min(100, (x1 / imageWidth) * 100));
  const topPercent = Math.max(0, Math.min(100, (y1 / imageHeight) * 100));
  const widthPercent = Math.max(0, Math.min(100 - leftPercent, ((x2 - x1) / imageWidth) * 100));
  const heightPercent = Math.max(0, Math.min(100 - topPercent, ((y2 - y1) / imageHeight) * 100));

  return { leftPercent, topPercent, widthPercent, heightPercent };
}

export function formatConfidence(conf: number): { percentage: string; level: 'high' | 'medium' | 'low' } {
  const percentage = `${Math.round((conf || 0) * 100)}%`;
  if (conf >= 0.85) return { percentage, level: 'high' };
  if (conf >= 0.60) return { percentage, level: 'medium' };
  return { percentage, level: 'low' };
}

export function cleanProductToken(token: string): boolean {
  const t = token.trim();
  if (!t) return false;
  // If token is pure digits (e.g. '255', '3', '1080')
  if (/^\d+$/.test(t)) return false;
  // If token is a random alphanumeric hash (e.g. 'imahgycfya2yx6nn', 'd3x89v', 'a1b2c3d4')
  if (t.length >= 7 && /\d/.test(t) && /[a-zA-Z]/.test(t)) return false;
  if (t.length >= 9 && !/[aeiouAEIOU]/.test(t)) return false;
  // Common asset noise words
  if (['jpg', 'png', 'jpeg', 'webp', 'img', 'image', 'photo', 'thumb', 'thumbnail', 'preview', 'upload', 'download'].includes(t.toLowerCase())) {
    return false;
  }
  return true;
}

export function cleanDisplayProductName(rawName?: string | null): string {
  if (!rawName || !rawName.trim()) return 'Untitled Inspection';
  const text = rawName.trim();
  if (['untitled inspection', 'untitled', 'product', 'image', 'photo'].includes(text.toLowerCase())) {
    return 'Untitled Inspection';
  }

  const rawTokens = text.split(/[\s\-_\/.]+/);
  const validTokens = rawTokens.filter(cleanProductToken);

  if (validTokens.length === 0) return 'Untitled Inspection';

  const seen = new Set<string>();
  const deduped: string[] = [];
  for (const t of validTokens) {
    const lower = t.toLowerCase();
    if (!seen.has(lower)) {
      seen.add(lower);
      deduped.push(t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
    }
  }

  const result = deduped.join(' ').trim();
  return result.length >= 2 ? result : 'Untitled Inspection';
}

export function cleanFilenameTitle(filename: string): string {
  if (!filename) return 'Untitled Inspection';
  const stem = filename.replace(/\.[^/.]+$/, '');

  // If stem is purely numeric or typical camera timestamp format like IMG_20260831_123456 or DSC_1234
  if (/^(?:img|dsc|photo|image|picture|sample|snapshot|p|pic|screenshot)?[\W_]*[0-9_\-\s]*$/i.test(stem)) {
    return 'Untitled Inspection';
  }

  const cleanNoPrefix = stem.replace(/^(?:img|dsc|photo|image|picture|sample|snapshot)\s*[0-9_\-]*\s*/i, '').trim();
  return cleanDisplayProductName(cleanNoPrefix || stem);
}

export function formatProductCompositeTitle(commodity?: string | null, brandOrMfg?: string | null, fallbackFilename?: string | null): string {
  const comm = commodity && commodity !== 'Untitled Inspection' ? cleanDisplayProductName(commodity) : '';
  const brand = brandOrMfg && brandOrMfg !== 'Untitled Inspection' ? cleanDisplayProductName(brandOrMfg) : '';

  if (comm && brand && comm !== 'Untitled Inspection' && brand !== 'Untitled Inspection') {
    if (brand.toLowerCase().includes(comm.toLowerCase()) || comm.toLowerCase().includes(brand.toLowerCase())) {
      return comm.length >= brand.length ? comm : `${comm} — ${brand}`;
    }
    return `${comm} — ${brand}`;
  }
  if (comm && comm !== 'Untitled Inspection') return comm;
  if (brand && brand !== 'Untitled Inspection') return brand;
  return cleanFilenameTitle(fallbackFilename || '');
}

export function getInspectionDisplayTitle(meta?: { display_name?: string; product_name?: string; inspection_id?: string }): string {
  if (!meta) return 'Untitled Inspection';
  if (meta.display_name && meta.display_name.trim()) {
    return meta.display_name.trim();
  }
  if (meta.product_name && meta.product_name.trim() && meta.product_name !== 'Untitled Inspection') {
    return cleanDisplayProductName(meta.product_name.trim());
  }
  return 'Untitled Inspection';
}
