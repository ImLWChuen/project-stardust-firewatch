import React from 'react';

export default function CoverageMap({ aoiId }: { aoiId: string }) {
  return (
    <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg h-72 flex items-center justify-center text-slate-400">
      Satellite Overpass &amp; Swath Coverage Map for {aoiId}
    </div>
  );
}
