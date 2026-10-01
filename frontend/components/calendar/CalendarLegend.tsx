import React from 'react';

export default function CalendarLegend() {
  return (
    <div className="flex items-center space-x-2 text-xs text-slate-400">
      <span>Low Activity</span>
      <span className="w-3 h-3 bg-slate-800 rounded"></span>
      <span className="w-3 h-3 bg-orange-400 rounded"></span>
      <span className="w-3 h-3 bg-orange-600 rounded"></span>
      <span className="w-3 h-3 bg-red-600 rounded"></span>
      <span>Peak Window</span>
    </div>
  );
}
