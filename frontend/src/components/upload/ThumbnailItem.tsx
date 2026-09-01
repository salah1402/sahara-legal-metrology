import React from 'react';
import type { InspectionImage } from '../../types/inspection';
import { X } from 'lucide-react';
import { formatFileSize } from '../../utils/formatters';

export interface ThumbnailItemProps {
  image: InspectionImage;
  index: number;
  isSelected?: boolean;
  onSelect?: () => void;
  onRemove?: () => void;
  isPrimary?: boolean;
}

export const ThumbnailItem: React.FC<ThumbnailItemProps> = ({
  image,
  index,
  isSelected = false,
  onSelect,
  onRemove,
  isPrimary = false,
}) => {
  return (
    <div
      onClick={onSelect}
      className={`group relative flex items-center gap-3 p-2 rounded-xl border transition-all cursor-pointer select-none ${
        isSelected
          ? 'border-primary-800 bg-primary-50/40 ring-1 ring-primary-800 shadow-sm'
          : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/70'
      }`}
    >
      {/* Image Thumbnail */}
      <div className="relative w-14 h-14 rounded-lg overflow-hidden bg-slate-100 border border-slate-200/80 flex-shrink-0 flex items-center justify-center">
        <img
          src={image.previewUrl}
          alt={image.name}
          className="w-full h-full object-cover"
        />
        {isPrimary && (
          <span className="absolute bottom-0 inset-x-0 bg-primary-900/90 text-white text-[9px] font-semibold text-center py-0.5 tracking-tighter">
            PRIMARY
          </span>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-slate-800 truncate">{image.name}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[11px] text-slate-400 font-mono">
            {formatFileSize(image.size)}
          </span>
          <span className="text-[10px] text-slate-400">• Image #{index + 1}</span>
        </div>
      </div>

      {/* Remove button */}
      <div className="flex items-center gap-1">
        {onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
            title="Remove image"
            aria-label="Remove image"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
