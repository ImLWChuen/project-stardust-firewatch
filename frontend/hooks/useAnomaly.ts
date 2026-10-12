import { useState } from 'react';

/** Hook managing anomaly detection data for a given area of interest. */
export function useAnomaly(aoiId: string) {
  const [anomaly, setAnomaly] = useState(null);
  return { anomaly, setAnomaly };
}
