import React, { useState } from 'react';
import type { OCRTextRegion } from '../../types/ocr';
import { formatConfidence } from '../../utils/bboxUtils';
import { Search, Copy, Check } from 'lucide-react';
import { clsx } from 'clsx';
import { showToast } from '../../hooks/useToast';

export interface OCRRegionListProps {
  regions: OCRTextRegion[];
  selectedRegionId: string | null;
  hoveredRegionId: string | null;
  onSelectRegion: (id: string | null) => void;
  onHoverRegion: (id: string | null) => void;
}

export const OCRRegionList: React.FC<OCRRegionListProps> = ({
  regions,
  selectedRegionId,
  hoveredRegionId,
  onSelectRegion,
  onHoverRegion,
}) => {
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredRegions = regions.filter((r) =>
    r.text.toLowerCase().includes(search.toLowerCase()) ||
    (r.fieldCategory && r.fieldCategory.toLowerCase().includes(search.toLowerCase()))
  );

  const handleCopyText = (text: string, id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    showToast('info', 'Copied to Clipboard', `"${text}"`);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-subtle">
      {/* Header & Search */}
      <div className="p-3.5 border-b border-slate-100 bg-slate-50/70 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Detected OCR Regions
            </span>
            <span className="text-[11px] font-mono font-semibold bg-slate-200/80 text-slate-700 px-1.5 py-0.2 rounded-full">
              {regions.length}
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">PaddleOCR v2.8</span>
        </div>

        {/* Search filter input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search detected text (e.g. 'MRP', 'Net', 'g')..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary-800"
          />
        </div>
      </div>

      {/* Region List Cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[540px]">
        {filteredRegions.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">
            No matching OCR regions found for "{search}"
          </div>
        ) : (
          filteredRegions.map((region) => {
            const isSelected = selectedRegionId === region.id;
            const isHovered = hoveredRegionId === region.id;
            const conf = formatConfidence(region.confidence);

            return (
              <div
                key={region.id}
                onClick={() => onSelectRegion(isSelected ? null : region.id)}
                onMouseEnter={() => onHoverRegion(region.id)}
                onMouseLeave={() => onHoverRegion(null)}
                className={clsx(
                  'p-2.5 rounded-xl border transition-all duration-150 cursor-pointer select-none space-y-1.5',
                  isSelected
                    ? 'border-emerald-500 bg-emerald-50/40 ring-1 ring-emerald-500 shadow-sm'
                    : isHovered
                    ? 'border-amber-400 bg-amber-50/30 shadow-subtle'
                    : 'border-slate-200/80 bg-white hover:bg-slate-50/80'
                )}
              >
                {/* Top Row: Field Category + Confidence Badge */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded font-mono">
                    {region.fieldCategory || 'raw text'}
                  </span>

                  <span
                    className={clsx(
                      'text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border',
                      conf.badgeClass
                    )}
                  >
                    {conf.percentage} conf
                  </span>
                </div>

                {/* Text Content */}
                <p className="text-xs font-mono font-medium text-slate-900 leading-snug break-words">
                  "{region.text}"
                </p>

                {/* Bottom Row: Bounding Box Coordinates + Copy button */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[10px] text-slate-400 font-mono">
                  <span>
                    bbox: [{region.bbox.join(', ')}]
                  </span>

                  <button
                    type="button"
                    onClick={(e) => handleCopyText(region.text, region.id, e)}
                    className="p-1 hover:text-slate-800 hover:bg-slate-100 rounded transition-colors"
                    title="Copy detected text"
                  >
                    {copiedId === region.id ? (
                      <Check className="w-3 h-3 text-emerald-600" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
