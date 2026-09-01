import React from 'react';
import { InstructionInput } from './InstructionInput';
import { DropzoneUpload } from '../upload/DropzoneUpload';
import { ThumbnailList } from '../upload/ThumbnailList';
import { ProcessingIndicator } from './ProcessingIndicator';
import { Button } from '../common/Button';
import { Play, AlertCircle, Scale } from 'lucide-react';
import type { InspectionImage, InspectionPipelineStage } from '../../types/inspection';

export interface HeroInspectionAreaProps {
  instructionPrompt: string;
  onInstructionChange: (val: string) => void;
  selectedImages: InspectionImage[];
  onFilesSelected: (files: File[]) => void;
  onOpenCamera: () => void;
  onRemoveImage: (id: string) => void;
  onSelectImageIndex: (index: number) => void;
  selectedImageIndex: number;
  onStartInspection: () => void;
  pipelineStage: InspectionPipelineStage;
  pipelineProgress: number;
  pipelineMessage: string;
  error: string | null;
}

export const HeroInspectionArea: React.FC<HeroInspectionAreaProps> = ({
  instructionPrompt,
  onInstructionChange,
  selectedImages,
  onFilesSelected,
  onOpenCamera,
  onRemoveImage,
  onSelectImageIndex,
  selectedImageIndex,
  onStartInspection,
  pipelineStage,
  pipelineProgress,
  pipelineMessage,
  error,
}) => {
  const isProcessing = pipelineStage !== 'idle' && pipelineStage !== 'complete' && pipelineStage !== 'error';

  return (
    <div className="space-y-4 sm:space-y-6 max-w-4xl mx-auto w-full">
      {/* Header Banner */}
      <div className="text-left space-y-1 sm:space-y-1.5 pt-1 w-full">
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-700 text-[11px] sm:text-xs font-semibold">
          <Scale className="w-3.5 h-3.5 text-primary-800 flex-shrink-0" />
          <span className="truncate">Legal Metrology (Packaged Commodities) Rules, 2011</span>
        </div>
        <h1 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
          New Package Inspection
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 max-w-2xl leading-relaxed">
          Upload or capture label images to evaluate mandatory statutory declarations, unit sales pricing, manufacturer details, and net quantity compliance under PCR 2011.
        </p>
      </div>

      {/* Processing Pipeline Indicator */}
      {isProcessing && (
        <ProcessingIndicator
          stage={pipelineStage}
          progress={pipelineProgress}
          message={pipelineMessage}
          error={error}
        />
      )}

      {/* Main Inspection Setup Card */}
      {!isProcessing && (
        <div className="bg-white rounded-2xl border border-slate-200 p-3.5 sm:p-5 md:p-6 shadow-subtle space-y-4 sm:space-y-5 w-full">
          {/* Natural Language Instruction */}
          <InstructionInput
            value={instructionPrompt}
            onChange={onInstructionChange}
            disabled={isProcessing}
            onSubmit={onStartInspection}
          />

          {/* Image Input Section */}
          <div className="space-y-3 pt-1 w-full">
            <DropzoneUpload
              onFilesSelected={onFilesSelected}
              onOpenCamera={onOpenCamera}
              disabled={isProcessing}
            />

            {/* Selected Image Thumbnails */}
            {selectedImages.length > 0 && (
              <ThumbnailList
                images={selectedImages}
                selectedIndex={selectedImageIndex}
                onSelectIndex={onSelectImageIndex}
                onRemoveImage={onRemoveImage}
              />
            )}
          </div>

          {/* Start Inspection Action Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 sm:pt-4 border-t border-slate-100 w-full">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
              <span className="truncate">
                {selectedImages.length === 0
                  ? 'Add at least one label image to begin'
                  : `${selectedImages.length} image(s) ready for inspection`}
              </span>
            </div>

            <Button
              type="button"
              variant="primary"
              size="lg"
              onClick={onStartInspection}
              disabled={selectedImages.length === 0 || isProcessing}
              leftIcon={<Play className="w-4 h-4 fill-current" />}
              className="w-full sm:w-auto px-6 py-2.5 font-semibold shadow-sm justify-center min-h-[42px]"
            >
              Start Inspection
            </Button>
          </div>
        </div>
      )}

      {/* Error state alert */}
      {error && !isProcessing && (
        <div className="p-3.5 sm:p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-800 w-full">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <span className="font-semibold block mb-0.5">Inspection Error</span>
            <span className="break-words">{error}</span>
          </div>
        </div>
      )}
    </div>
  );
};
