import React from 'react';

export default function CriticalPeriod() {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-200">Active Peak Window</h4>
      <p className="text-lg font-semibold text-red-400 mt-2">Feb 20 - Mar 15</p>
      <span className="text-xs text-slate-400">Post-Harvest Agricultural Burning</span>
    </div>
  );
}
