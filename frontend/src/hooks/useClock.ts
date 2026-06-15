import { useEffect, useState } from 'react';

/** Re-renders every `intervalMs` so components can show a live, ticking clock. */
export function useClock(intervalMs = 1000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
