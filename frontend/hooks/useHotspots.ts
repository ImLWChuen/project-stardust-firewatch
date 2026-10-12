import { useState } from 'react';

/** Hook managing the list of fire hotspots. */
export function useHotspots() {
  const [hotspots, setHotspots] = useState([]);
  return { hotspots, setHotspots };
}
