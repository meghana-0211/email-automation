'use client';

import {Toaster} from Sonner

export function ToastProvider() {
  return <Toaster richColors position="top-right" />;
}

export function toast() {
  return {
    success: (message) => {
      import('Sonner').then(({ toast }) => {
        toast.success(message);
      });
    },
    error: (message) => {
      import('Sonner').then(({ toast }) => {
        toast.error(message);
      });
    },
    info: (message) => {
      import('Sonner').then(({ toast }) => {
        toast.info(message);
      });
    }
  };
}