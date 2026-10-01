import React from 'react';

export default function SensorBadge({ sensor }: { sensor: string }) {
  const isModis = sensor.toUpperCase().includes('MODIS');
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
      isModis 
        ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
        : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    }`}>
      {sensor}
    </span>
  );
}
