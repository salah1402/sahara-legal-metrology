import React from 'react';
import { useToast, dismissToast } from '../../hooks/useToast';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import { clsx } from 'clsx';

export const ToastContainer: React.FC = () => {
  const { toasts } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 left-3 right-3 sm:left-auto sm:right-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none mx-auto sm:mx-0">
      {toasts.map((toast) => {
        const getIcon = () => {
          switch (toast.type) {
            case 'success':
              return <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />;
            case 'error':
              return <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0" />;
            case 'warning':
              return <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />;
            case 'info':
            default:
              return <Info className="w-5 h-5 text-blue-600 flex-shrink-0" />;
          }
        };

        const getBorderColor = () => {
          switch (toast.type) {
            case 'success':
              return 'border-emerald-200 bg-emerald-50/95 text-emerald-900 shadow-md';
            case 'error':
              return 'border-rose-200 bg-rose-50/95 text-rose-900 shadow-md';
            case 'warning':
              return 'border-amber-200 bg-amber-50/95 text-amber-900 shadow-md';
            case 'info':
            default:
              return 'border-blue-200 bg-blue-50/95 text-blue-900 shadow-md';
          }
        };

        return (
          <div
            key={toast.id}
            className={clsx(
              'pointer-events-auto flex items-start gap-2.5 p-3 rounded-xl border shadow-popover backdrop-blur-md transition-all duration-200 animate-slide-up w-full',
              getBorderColor()
            )}
          >
            {getIcon()}
            <div className="flex-1 min-w-0">
              <h4 className="text-xs font-semibold leading-tight">{toast.title}</h4>
              {toast.message && (
                <p className="text-xs opacity-90 mt-0.5 leading-snug break-words">{toast.message}</p>
              )}
            </div>
            <button
              onClick={() => dismissToast(toast.id)}
              className="text-slate-400 hover:text-slate-700 p-1 rounded-lg transition-colors flex-shrink-0 min-w-[28px] min-h-[28px] flex items-center justify-center -mr-1 -mt-1"
              aria-label="Dismiss toast"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
