import React from 'react';

export default function DataQualityPanel() {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-200">Data Quality &amp; Confidence</h4>
      <div className="mt-2 text-xs text-slate-400">
        <div>Cloud Obscuration: &lt; 8%</div>
        <div>Mean Confidence: 91.2%</div>
      </div>
    </div>
  );
}
