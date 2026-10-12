import React from 'react';

/** Renders the map legend explaining hotspot intensity (FRP) color coding. */
export default function MapLegend() {
  return (
    <div className="p-3 bg-slate-900 border border-slate-800 rounded text-xs space-y-1">
      <div className="font-semibold text-slate-300">Hotspot Intensity (FRP)</div>
      <div className="flex items-center space-x-2 text-slate-400">
        <span className="w-3 h-3 rounded-full bg-yellow-400"></span>
        <span>Low (&lt;10 MW)</span>
        <span className="w-3 h-3 rounded-full bg-orange-500"></span>
        <span>Medium (10-50 MW)</span>
        <span className="w-3 h-3 rounded-full bg-red-600"></span>
        <span>High (&gt;50 MW)</span>
      </div>
    </div>
  );
}
