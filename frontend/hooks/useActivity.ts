import { useState } from 'react';

/** Hook managing harmonized fire activity data for a given area of interest. */
export function useActivity(aoiId: string) {
  const [activity, setActivity] = useState(null);
  return { activity, setActivity };
}
