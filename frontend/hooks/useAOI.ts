import { useState, useEffect } from 'react';

export function useAOI() {
  const [selectedAOI, setSelectedAOI] = useState('kedah');
  return { selectedAOI, setSelectedAOI };
}
