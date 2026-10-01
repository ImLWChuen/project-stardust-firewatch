import React from 'react';

export default function CoverageQualityBadge({ score }: { score: number }) {
  const isGood = score >= 0.8;
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${
      isGood ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
    }`}>
      Coverage: {Math.round(score * 100)}%
    </span>
  );
}
