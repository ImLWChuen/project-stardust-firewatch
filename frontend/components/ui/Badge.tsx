import React from 'react';

/** Generic styled badge used to highlight short pieces of information. */
export default function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: string }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-orange-500/10 text-orange-400 border border-orange-500/20">
      {children}
    </span>
  );
}
