import React from 'react';
import type { InspectionImage } from '../../types/inspection';
import { ThumbnailItem } from './ThumbnailItem';
import { Image as ImageIcon } from 'lucide-react';

export interface ThumbnailListProps {
  images: InspectionImage[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onRemoveImage?: (id: string) => void;
}

export const ThumbnailList: React.FC<ThumbnailListProps> = ({
  images,
  selectedIndex,
  onSelectIndex,
  onRemoveImage,
}) => {
  if (images.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
          <ImageIcon className="w-3.5 h-3.5 text-slate-500" />
          <span>Product Images ({images.length})</span>
        </span>
        <span className="text-[11px] text-slate-400">
          Click image to inspect
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {images.map((image, idx) => (
          <ThumbnailItem
            key={image.id}
            image={image}
            index={idx}
            isSelected={selectedIndex === idx}
            onSelect={() => onSelectIndex(idx)}
            onRemove={onRemoveImage ? () => onRemoveImage(image.id) : undefined}
            isPrimary={idx === 0}
          />
        ))}
      </div>
    </div>
  );
};
