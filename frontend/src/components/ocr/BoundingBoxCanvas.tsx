import React, { useState, useRef } from 'react';
import type { OCRRegion } from '../../types/ocr';
import { normalizeBoundingBox, formatConfidence } from '../../utils/formatters';
import { ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff } from 'lucide-react';
import { clsx } from 'clsx';

export interface BoundingBoxCanvasProps {
  imageUrl: string;
  imageName: string;
  regions: OCRRegion[];
  selectedRegionId: string | null;
  hoveredRegionId: string | null;
  onSelectRegion: (id: string | null) => void;
  onHoverRegion: (id: string | null) => void;
  showBoxes: boolean;
  onToggleShowBoxes: () => void;
}

export const BoundingBoxCanvas: React.FC<BoundingBoxCanvasProps> = ({
  imageUrl,
  imageName,
  regions,
  selectedRegionId,
  hoveredRegionId,
  onSelectRegion,
  onHoverRegion,
  showBoxes,
  onToggleShowBoxes,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number }>({ width: 1, height: 1 });
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 2.5));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.25, 0.75));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
  };

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const target = e.currentTarget;
    setNaturalSize({
      width: target.naturalWidth || 1,
      height: target.naturalHeight || 1,
    });
  };

  const boxesToRender = showBoxes
    ? regions
    : regions.filter((r) => r.id === selectedRegionId || r.id === hoveredRegionId);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-subtle flex flex-col w-full">
      {/* Top Toolbar: Fluid & Responsive */}
      <div className="px-3 py-2 sm:px-3.5 sm:py-2.5 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between gap-2 flex-wrap w-full">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <span className="text-xs font-bold text-slate-800 truncate max-w-[130px] sm:max-w-[200px]" title={imageName}>
            {imageName}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 bg-slate-200/80 rounded text-slate-600 flex-shrink-0">
            {naturalSize.width}×{naturalSize.height}
          </span>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
          {/* Toggle OCR Boxes */}
          <button
            type="button"
            onClick={onToggleShowBoxes}
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors min-h-[32px]',
              showBoxes
                ? 'bg-primary-50 text-primary-800 border border-primary-200 shadow-2xs font-semibold'
                : 'bg-white text-slate-700 hover:text-slate-900 border border-slate-200'
            )}
            title={showBoxes ? 'Hide all OCR bounding boxes' : 'Show all OCR bounding boxes'}
          >
            {showBoxes ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span className="text-[11px] sm:text-xs">{showBoxes ? 'Hide Boxes' : 'Show Boxes'}</span>
          </button>

          {/* Zoom Controls */}
          <div className="flex items-center bg-white rounded-lg border border-slate-200 p-0.5 shadow-2xs">
            <button
              type="button"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.75}
              className="p-1 hover:bg-slate-100 rounded text-slate-600 disabled:opacity-30 min-w-[26px] min-h-[26px] flex items-center justify-center"
              title="Zoom out"
              aria-label="Zoom out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] font-mono px-1 text-slate-700 min-w-[32px] text-center font-medium">
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              type="button"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 2.5}
              className="p-1 hover:bg-slate-100 rounded text-slate-600 disabled:opacity-30 min-w-[26px] min-h-[26px] flex items-center justify-center"
              title="Zoom in"
              aria-label="Zoom in"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="p-1 hover:bg-slate-100 rounded text-slate-500 ml-0.5 min-w-[26px] min-h-[26px] flex items-center justify-center"
              title="Reset zoom"
              aria-label="Reset zoom"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Image Viewport: Clean Light Background Hugging Natural Image Height */}
      <div
        ref={containerRef}
        className="relative overflow-auto p-2 sm:p-3 flex items-center justify-center bg-slate-100/50 min-h-[180px] sm:min-h-[240px] w-full"
      >
        <div
          className="relative inline-block transition-transform duration-150 origin-center max-w-full"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          {/* Label Image */}
          <img
            ref={imgRef}
            src={imageUrl}
            alt={imageName}
            onLoad={handleImageLoad}
            className="max-h-[380px] sm:max-h-[580px] w-auto max-w-full rounded-lg shadow-md block object-contain pointer-events-auto"
          />

          {/* Bounding Box Overlays */}
          {boxesToRender.map((region) => {
            const bbox = normalizeBoundingBox(
              region.bbox,
              naturalSize.width,
              naturalSize.height
            );
            const isSelected = selectedRegionId === region.id;
            const isHovered = hoveredRegionId === region.id;

            return (
              <div
                key={region.id}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectRegion(isSelected ? null : region.id);
                }}
                onMouseEnter={() => onHoverRegion(region.id)}
                onMouseLeave={() => onHoverRegion(null)}
                style={{
                  left: `${bbox.leftPercent}%`,
                  top: `${bbox.topPercent}%`,
                  width: `${bbox.widthPercent}%`,
                  height: `${bbox.heightPercent}%`,
                }}
                className={clsx(
                  'absolute cursor-pointer transition-all duration-150 rounded-xs group',
                  isSelected
                    ? 'border-2 border-emerald-500 bg-emerald-500/25 ring-2 ring-emerald-400/60 z-30 shadow-md'
                    : isHovered
                    ? 'border-2 border-amber-500 bg-amber-400/25 z-20 shadow-sm'
                    : 'border border-blue-500/80 bg-blue-500/10 hover:bg-blue-500/25 z-10'
                )}
              >
                {/* Tooltip on hover/selection */}
                {(isSelected || isHovered) && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-0.5 bg-slate-900 text-white text-[11px] rounded shadow-lg border border-slate-700 whitespace-nowrap pointer-events-none z-40 flex items-center gap-1.5 font-sans max-w-[200px] truncate">
                    <span className="font-mono truncate">{region.text}</span>
                    <span className="text-[10px] px-1 bg-slate-800 rounded text-emerald-400 font-semibold font-mono flex-shrink-0">
                      {formatConfidence(region.confidence).percentage}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="px-3 py-1.5 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 flex items-center justify-between w-full">
        <span className="flex items-center gap-1.5 truncate">
          <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', showBoxes ? 'bg-primary-800' : 'bg-emerald-500')} />
          <span className="truncate">
            {showBoxes
              ? `${regions.length} text regions displayed`
              : `${regions.length} regions (Clean view)`}
          </span>
        </span>
        <span className="text-slate-400 text-[10px] hidden sm:inline ml-2 flex-shrink-0">
          {showBoxes ? 'Click bounding boxes to inspect' : 'Select evidence items to highlight'}
        </span>
      </div>
    </div>
  );
};
