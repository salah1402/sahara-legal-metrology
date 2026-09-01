import React, { useRef, useState } from 'react';
import { UploadCloud, Camera, ImagePlus } from 'lucide-react';
import { Button } from '../common/Button';

export interface DropzoneUploadProps {
  onFilesSelected: (files: File[]) => void;
  onOpenCamera: () => void;
  disabled?: boolean;
}

export const DropzoneUpload: React.FC<DropzoneUploadProps> = ({
  onFilesSelected,
  onOpenCamera,
  disabled = false,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return;
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const filesArray = Array.from(e.dataTransfer.files);
      onFilesSelected(filesArray);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      onFilesSelected(filesArray);
      // Reset input value so same file can be re-selected if removed
      e.target.value = '';
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative rounded-2xl border-2 border-dashed transition-all duration-200 p-4 sm:p-6 text-center w-full ${
        isDragOver
          ? 'border-primary-600 bg-primary-50/50 scale-[1.005]'
          : 'border-slate-200 hover:border-slate-300 bg-white/70 hover:bg-slate-50/40'
      } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,image/jpg"
        onChange={handleFileInputChange}
        className="hidden"
        id="label-image-upload"
      />

      <div className="flex flex-col items-center justify-center w-full">
        <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-primary-50 border border-primary-100 flex items-center justify-center text-primary-800 mb-2 sm:mb-3 shadow-subtle">
          <UploadCloud className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>

        <h4 className="text-xs sm:text-sm font-semibold text-slate-800 mb-1">
          Upload commodity label photos
        </h4>
        <p className="text-[11px] sm:text-xs text-slate-500 mb-3 sm:mb-4 max-w-sm px-2">
          Drag & drop images here, or choose an input source below. Supports JPG, PNG, WEBP.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 w-full sm:w-auto">
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            leftIcon={<ImagePlus className="w-4 h-4" />}
            className="w-full justify-center min-h-[38px]"
          >
            Upload photo
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onOpenCamera}
            leftIcon={<Camera className="w-4 h-4 text-slate-600" />}
            className="w-full justify-center min-h-[38px]"
          >
            Take photo
          </Button>
        </div>
      </div>
    </div>
  );
};
