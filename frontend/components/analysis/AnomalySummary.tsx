import React from 'react';

export default function AnomalySummary() {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-200">Anomaly Rating</h4>
      <p className="text-2xl font-bold text-emerald-400 mt-2">+0.4 &sigma;</p>
      <span className="text-xs text-slate-400">Near Normal Seasonal Mean</span>
    </div>
  );
}
