import { useState } from 'react';

export function useActivity(aoiId: string) {
  const [activity, setActivity] = useState(null);
  return { activity, setActivity };
}
