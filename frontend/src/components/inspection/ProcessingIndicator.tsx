import React from 'react';
import type { InspectionPipelineStage } from '../../types/inspection';
import { CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

export interface ProcessingIndicatorProps {
  stage: InspectionPipelineStage;
  progress: number;
  message?: string;
  error?: string | null;
}

const STAGES = [
  { id: 'preparing_image', label: 'Preparing image', stageIndex: 1 },
  { id: 'processing_ocr', label: 'OCR processing (PaddleOCR)', stageIndex: 2 },
  { id: 'understanding_label', label: 'Understanding label (Nemotron)', stageIndex: 3 },
  { id: 'complete', label: 'Structured Data Ready', stageIndex: 4 },
];

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({
  stage,
  progress,
  message,
  error,
}) => {
  if (stage === 'idle') return null;

  const currentStageIndex = (() => {
    switch (stage) {
      case 'preparing_image': return 1;
      case 'processing_ocr': return 2;
      case 'understanding_label': return 3;
      case 'complete': return 4;
      case 'error': return -1;
      default: return 0;
    }
  })();

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-card animate-fade-in space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {stage === 'error' ? (
            <div className="w-9 h-9 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertCircle className="w-5 h-5" />
            </div>
          ) : stage === 'complete' ? (
            <div className="w-9 h-9 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-9 h-9 rounded-full bg-primary-50 text-primary-800 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          )}

          <div>
            <h4 className="text-sm font-semibold text-slate-800">
              {stage === 'error'
                ? 'Processing Failed'
                : stage === 'complete'
                ? 'Structured Data Ready'
                : 'Processing Label Inspection'}
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">
              {error || message || 'Executing multi-stage analysis pipeline'}
            </p>
          </div>
        </div>

        <span className="text-xs font-mono font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md">
          {progress}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
        <div
          className={clsx(
            'h-full transition-all duration-300 ease-out rounded-full',
            stage === 'error'
              ? 'bg-rose-500'
              : stage === 'complete'
              ? 'bg-emerald-500'
              : 'bg-primary-800'
          )}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Stage Steps */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100">
        {STAGES.map((s) => {
          const isFinished = currentStageIndex > s.stageIndex || stage === 'complete';
          const isCurrent = currentStageIndex === s.stageIndex;

          return (
            <div
              key={s.id}
              className={clsx(
                'flex sm:flex-col items-center gap-2 p-2 rounded-lg text-xs transition-colors',
                isCurrent
                  ? 'bg-primary-50 text-primary-900 font-semibold'
                  : isFinished
                  ? 'text-emerald-700 bg-emerald-50/50'
                  : 'text-slate-400 bg-transparent'
              )}
            >
              <div className="flex items-center justify-center flex-shrink-0">
                {isFinished ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-primary-800 animate-spin" />
                ) : (
                  <span className="w-4 h-4 rounded-full border border-slate-300 text-[10px] flex items-center justify-center text-slate-400 font-mono">
                    {s.stageIndex}
                  </span>
                )}
              </div>
              <span className="text-left sm:text-center text-[11px] leading-tight">
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
