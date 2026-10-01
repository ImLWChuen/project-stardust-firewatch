import { useState } from 'react';

export function useHotspots() {
  const [hotspots, setHotspots] = useState([]);
  return { hotspots, setHotspots };
}
