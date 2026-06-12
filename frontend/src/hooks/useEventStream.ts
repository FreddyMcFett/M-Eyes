import { useEffect, useRef, useState } from 'react';
import { getToken } from '../api/client';

export interface LiveEvent {
  kind: string;
  id: number;
  ts: string;
  severity: string;
  category: string;
  message: string;
}

/** Subscribes to the SSE live event stream; keeps the most recent `max` events. */
export function useEventStream(max = 50, enabled = true) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const token = getToken();
    if (!token) return;
    const source = new EventSource(`/api/v1/events/stream?token=${encodeURIComponent(token)}`);
    sourceRef.current = source;
    source.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as LiveEvent;
        setEvents((current) => [event, ...current].slice(0, max));
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [max, enabled]);

  return events;
}
