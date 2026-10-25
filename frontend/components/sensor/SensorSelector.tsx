import React from 'react';

/** Renders buttons for filtering displayed data by sensor. */
export default function SensorSelector() {
  return (
    <div className="flex items-center space-x-2 text-xs">
      <button className="px-2 py-1 bg-slate-800 text-white rounded border border-slate-700">All Sensors</button>
      <button className="px-2 py-1 bg-slate-900 text-slate-400 rounded border border-slate-800">MODIS</button>
      <button className="px-2 py-1 bg-slate-900 text-slate-400 rounded border border-slate-800">VIIRS</button>
    </div>
  );
}
