import React from 'react';

/** Site-wide header displaying the application brand and tagline. */
export default function Header() {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <span className="text-orange-500 font-extrabold text-xl">STARDUST</span>
        <span className="text-xs uppercase bg-orange-500/10 text-orange-400 px-2 py-0.5 rounded border border-orange-500/20">Satellite Harmonization</span>
      </div>
    </header>
  );
}
