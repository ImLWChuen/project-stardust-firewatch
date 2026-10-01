import React from 'react';

export default function Sidebar() {
  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/30 p-4 space-y-2">
      <nav className="space-y-1 text-sm text-slate-300">
        <div className="px-3 py-2 rounded bg-slate-800 text-white font-medium">Dashboard</div>
        <div className="px-3 py-2 rounded hover:bg-slate-800/60 cursor-pointer">Burning Calendar</div>
        <div className="px-3 py-2 rounded hover:bg-slate-800/60 cursor-pointer">Harmonization</div>
        <div className="px-3 py-2 rounded hover:bg-slate-800/60 cursor-pointer">Validation</div>
      </nav>
    </aside>
  );
}
