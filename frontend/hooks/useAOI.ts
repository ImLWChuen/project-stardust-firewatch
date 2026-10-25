import { useState, useEffect } from 'react';

/** Hook managing the currently selected area of interest. */
export function useAOI() {
  const [selectedAOI, setSelectedAOI] = useState('kedah');
  return { selectedAOI, setSelectedAOI };
}
