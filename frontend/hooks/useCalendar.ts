import { useState } from 'react';

export function useCalendar(aoiId: string, year: number) {
  const [calendarData, setCalendarData] = useState(null);
  return { calendarData, setCalendarData };
}
