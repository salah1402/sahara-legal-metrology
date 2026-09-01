/**
 * Bounding Box Calculation and Normalization Utilities
 * Handles mapping coordinates [x1, y1, x2, y2] to responsive image element dimensions
 */

export interface NormalizedBBox {
  leftPercent: number;
  topPercent: number;
  widthPercent: number;
  heightPercent: number;
}

/**
 * Convert pixel bounding box [x1, y1, x2, y2] into percentage dimensions relative to original image size
 */
export function normalizeBoundingBox(
  bbox: [number, number, number, number],
  originalWidth: number,
  originalHeight: number
): NormalizedBBox {
  const [x1, y1, x2, y2] = bbox;
  const safeW = Math.max(originalWidth, 1);
  const safeH = Math.max(originalHeight, 1);

  const leftPercent = (Math.min(x1, x2) / safeW) * 100;
  const topPercent = (Math.min(y1, y2) / safeH) * 100;
  const widthPercent = (Math.abs(x2 - x1) / safeW) * 100;
  const heightPercent = (Math.abs(y2 - y1) / safeH) * 100;

  return {
    leftPercent: Math.max(0, Math.min(leftPercent, 100)),
    topPercent: Math.max(0, Math.min(topPercent, 100)),
    widthPercent: Math.max(0.5, Math.min(widthPercent, 100 - leftPercent)),
    heightPercent: Math.max(0.5, Math.min(heightPercent, 100 - topPercent)),
  };
}

/**
 * Format confidence score into readable percentage with color variant
 */
export function formatConfidence(score: number): {
  percentage: string;
  colorClass: string;
  badgeClass: string;
} {
  const pct = Math.round(score * 100);
  if (pct >= 90) {
    return {
      percentage: `${pct}%`,
      colorClass: 'text-emerald-700 font-semibold',
      badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    };
  }
  if (pct >= 75) {
    return {
      percentage: `${pct}%`,
      colorClass: 'text-amber-700 font-medium',
      badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
    };
  }
  return {
    percentage: `${pct}%`,
    colorClass: 'text-rose-700 font-medium',
    badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
  };
}
