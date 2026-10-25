import React from 'react';

/** Generic styled container card with optional additional class names. */
export default function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`p-4 bg-slate-900 border border-slate-800 rounded-lg ${className}`}>
      {children}
    </div>
  );
}
