import React from 'react';

/** Displays the breakdown of fire detections by contributing sensor. */
export default function SensorBreakdown() {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg">
      <h4 className="text-sm font-semibold text-slate-200">Sensor Detections Breakdown</h4>
      <div className="mt-2 text-xs space-y-1 text-slate-400">
        <div>MODIS: 24%</div>
        <div>VIIRS (SNPP): 38%</div>
        <div>VIIRS (NOAA-20/21): 38%</div>
      </div>
    </div>
  );
}
