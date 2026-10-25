import React from 'react';

/** Renders the annual burning calendar grid, one cell per month. */
export default function BurningCalendar() {
  return (
    <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl">
      <h3 className="text-lg font-semibold text-white mb-4">Annual Burning Calendar</h3>
      <div className="grid grid-cols-12 gap-2 text-xs text-slate-400">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="h-16 bg-slate-800/60 rounded flex items-center justify-center">
            M{i + 1}
          </div>
        ))}
      </div>
    </div>
  );
}
