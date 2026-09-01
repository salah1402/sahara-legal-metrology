import React, { useEffect, useRef } from 'react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { useCamera } from '../../hooks/useCamera';
import { Camera, SwitchCamera, AlertCircle, Sparkles, Upload } from 'lucide-react';

export interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPhotoCaptured: (file: File) => void;
}

export const CameraModal: React.FC<CameraModalProps> = ({
  isOpen,
  onClose,
  onPhotoCaptured,
}) => {
  const {
    videoRef,
    isActive,
    error,
    startCamera,
    stopCamera,
    toggleFacingMode,
    capturePhoto,
  } = useCamera();

  const fileCaptureInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      startCamera();
    } else {
      stopCamera();
    }
  }, [isOpen, startCamera, stopCamera]);

  const handleCapture = async () => {
    const result = await capturePhoto();
    if (result) {
      onPhotoCaptured(result.file);
      onClose();
    }
  };

  const handleMobileFileFallback = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onPhotoCaptured(e.target.files[0]);
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="lg"
      title="Capture Product Label Photo"
      subtitle="Position the packaged commodity label within clear lighting"
    >
      <div className="space-y-4">
        {/* Viewfinder Container */}
        <div className="relative aspect-[4/3] sm:aspect-video w-full bg-slate-950 rounded-xl overflow-hidden flex items-center justify-center border border-slate-800 shadow-inner">
          {error ? (
            <div className="p-6 text-center text-slate-300 max-w-sm">
              <AlertCircle className="w-10 h-10 text-amber-400 mx-auto mb-2.5" />
              <h4 className="text-sm font-semibold text-white mb-1">Camera Inactive</h4>
              <p className="text-xs text-slate-400 mb-4">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="bg-white/10 text-white border-white/20 hover:bg-white/20"
                onClick={() => fileCaptureInputRef.current?.click()}
                leftIcon={<Upload className="w-4 h-4" />}
              >
                Use Device Camera / Gallery
              </Button>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />

              {/* Viewfinder Overlay Guides */}
              <div className="absolute inset-4 pointer-events-none border border-white/20 rounded-lg">
                {/* Crosshairs & corner brackets */}
                <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary-400" />
                <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary-400" />
                <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary-400" />
                <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary-400" />
              </div>

              {/* Live Badge */}
              <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-full flex items-center gap-1.5 text-[11px] text-white">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="font-mono text-[10px]">LIVE FEED</span>
              </div>

              {/* Flip camera button */}
              <button
                type="button"
                onClick={toggleFacingMode}
                className="absolute top-3 right-3 p-2 bg-black/60 hover:bg-black/80 text-white rounded-full backdrop-blur-md transition-colors"
                title="Switch front/back camera"
                aria-label="Switch camera"
              >
                <SwitchCamera className="w-4 h-4" />
              </button>
            </>
          )}
        </div>

        {/* Hidden mobile camera capture fallback */}
        <input
          ref={fileCaptureInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleMobileFileFallback}
          className="hidden"
        />

        {/* Shutter controls */}
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileCaptureInputRef.current?.click()}
            leftIcon={<Camera className="w-3.5 h-3.5" />}
          >
            System Native Camera
          </Button>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="regulatory"
              size="md"
              disabled={!isActive}
              onClick={handleCapture}
              leftIcon={<Sparkles className="w-4 h-4 text-amber-300" />}
            >
              Capture Label
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};
