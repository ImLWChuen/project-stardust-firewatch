import { useState } from 'react';

/** Hook managing burning calendar data for a given area of interest and year. */
export function useCalendar(aoiId: string, year: number) {
  const [calendarData, setCalendarData] = useState(null);
  return { calendarData, setCalendarData };
}
