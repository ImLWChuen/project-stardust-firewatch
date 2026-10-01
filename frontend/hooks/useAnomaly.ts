import { useState } from 'react';

export function useAnomaly(aoiId: string) {
  const [anomaly, setAnomaly] = useState(null);
  return { anomaly, setAnomaly };
}
