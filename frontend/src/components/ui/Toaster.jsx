import React from 'react';
import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster 
      position="top-right" 
      theme="dark" 
      duration={3000} 
      toastOptions={{
        style: {
          background: '#15181e',
          color: '#fff',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
          borderRadius: '0.75rem'
        },
        classNames: {
          toast: 'border border-zinc-700/40',
          success: '!border-l-4 !border-l-emerald-500 [&_svg]:text-emerald-500',
          error: '!border-l-4 !border-l-red-500 [&_svg]:text-red-500',
          warning: '!border-l-4 !border-l-amber-500 [&_svg]:text-amber-500'
        },
        className: 'tracking-wide font-medium'
      }}
    />
  );
}
