import React from 'react';

/** Wraps children with a hover-activated tooltip displaying the given text. */
export default function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <div className="relative group inline-block">
      {children}
      <span className="absolute bottom-full mb-1 hidden group-hover:block bg-slate-800 text-white text-xs px-2 py-1 rounded shadow">
        {text}
      </span>
    </div>
  );
}
