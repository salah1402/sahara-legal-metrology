import React from 'react';
import type { InspectionStatus } from '../../types/inspection';
import { CheckCircle2, AlertTriangle, XCircle, Clock, Search, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface StatusChipProps {
  status: InspectionStatus;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

export const StatusChip: React.FC<StatusChipProps> = ({
  status,
  size = 'md',
  showIcon = true,
  className,
}) => {
  const getStatusConfig = (status: InspectionStatus) => {
    switch (status) {
      case 'Compliant':
        return {
          label: 'Compliant',
          bg: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
          dot: 'bg-emerald-500',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
        };
      case 'Non-Compliant':
        return {
          label: 'Non-Compliant',
          bg: 'bg-rose-50 text-rose-800 border-rose-200/80',
          dot: 'bg-rose-500',
          icon: <XCircle className="w-3.5 h-3.5 text-rose-600" />,
        };
      case 'Needs Review':
        return {
          label: 'Needs Review',
          bg: 'bg-amber-50 text-amber-800 border-amber-200/80',
          dot: 'bg-amber-500',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />,
        };
      case 'OCR Complete':
        return {
          label: 'OCR Complete',
          bg: 'bg-blue-50 text-blue-800 border-blue-200/80',
          dot: 'bg-blue-500',
          icon: <FileText className="w-3.5 h-3.5 text-blue-600" />,
        };
      case 'OCR Processing':
        return {
          label: 'OCR Processing',
          bg: 'bg-indigo-50 text-indigo-800 border-indigo-200/80',
          dot: 'bg-indigo-500 animate-pulse',
          icon: <Search className="w-3.5 h-3.5 text-indigo-600 animate-spin" />,
        };
      case 'Under Review':
        return {
          label: 'Under Review',
          bg: 'bg-slate-100 text-slate-800 border-slate-200',
          dot: 'bg-slate-500',
          icon: <Clock className="w-3.5 h-3.5 text-slate-600" />,
        };
      case 'New':
      default:
        return {
          label: 'Draft / New',
          bg: 'bg-slate-100 text-slate-600 border-slate-200',
          dot: 'bg-slate-400',
          icon: <Clock className="w-3.5 h-3.5 text-slate-400" />,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <span
      className={twMerge(
        clsx(
          'inline-flex items-center font-medium border rounded-full select-none whitespace-nowrap',
          size === 'sm' ? 'text-[11px] px-2 py-0.5 gap-1.5' : 'text-xs px-2.5 py-1 gap-1.5',
          config.bg,
          className
        )
      )}
    >
      {showIcon ? (
        config.icon
      ) : (
        <span className={clsx('w-1.5 h-1.5 rounded-full', config.dot)} />
      )}
      <span>{config.label}</span>
    </span>
  );
};
