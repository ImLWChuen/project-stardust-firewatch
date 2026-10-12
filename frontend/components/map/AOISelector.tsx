import React from 'react';

/** Renders a dropdown for selecting the active area of interest. */
export default function AOISelector() {
  return (
    <select className="bg-slate-900 border border-slate-800 text-slate-200 text-sm rounded px-3 py-2">
      <option value="kedah">Kedah, Malaysia</option>
      <option value="riau">Riau, Indonesia</option>
      <option value="punjab">Punjab, India</option>
    </select>
  );
}
