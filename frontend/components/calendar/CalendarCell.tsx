import React from 'react';

export default function CalendarCell({ date, intensity }: { date: string; intensity: number }) {
  return (
    <div className="w-4 h-4 rounded-sm bg-orange-500/40" title={`${date}: ${intensity}`} />
  );
}
