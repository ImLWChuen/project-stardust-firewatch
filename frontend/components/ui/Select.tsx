import React from 'react';

export default function Select({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className="bg-slate-900 border border-slate-800 text-slate-200 text-sm rounded px-3 py-2" {...props}>
      {children}
    </select>
  );
}
