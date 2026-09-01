import { useState, useCallback } from 'react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
  duration?: number;
}

let toastListeners: ((toasts: ToastMessage[]) => void)[] = [];
let toastsState: ToastMessage[] = [];

function notifyListeners() {
  toastListeners.forEach(listener => listener([...toastsState]));
}

export function showToast(type: ToastMessage['type'], title: string, message?: string, duration = 4000) {
  const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
  const newToast: ToastMessage = { id, type, title, message, duration };
  toastsState = [...toastsState, newToast];
  notifyListeners();

  if (duration > 0) {
    setTimeout(() => {
      dismissToast(id);
    }, duration);
  }
}

export function dismissToast(id: string) {
  toastsState = toastsState.filter(t => t.id !== id);
  notifyListeners();
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>(toastsState);

  // Subscribe on mount
  useState(() => {
    const listener = (newToasts: ToastMessage[]) => setToasts(newToasts);
    toastListeners.push(listener);
    return () => {
      toastListeners = toastListeners.filter(l => l !== listener);
    };
  });

  const toast = useCallback((type: ToastMessage['type'], title: string, message?: string, duration?: number) => {
    showToast(type, title, message, duration);
  }, []);

  return {
    toasts,
    toast,
    dismissToast,
    toastSuccess: (title: string, msg?: string) => showToast('success', title, msg),
    toastError: (title: string, msg?: string) => showToast('error', title, msg),
    toastInfo: (title: string, msg?: string) => showToast('info', title, msg),
    toastWarning: (title: string, msg?: string) => showToast('warning', title, msg),
  };
}
