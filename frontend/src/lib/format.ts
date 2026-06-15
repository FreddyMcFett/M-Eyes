/** Human-readable byte size (binary units): 1536 → "1.5 KiB". */
export function formatBytes(bytes: number | null | undefined, digits = 1): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(digits)} ${units[unit]}`;
}

/** Compact duration from seconds: 90061 → "1d 1h 1m". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—';
  const s = Math.max(0, Math.floor(seconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (days) return `${days}d ${hours}h ${mins}m`;
  if (hours) return `${hours}h ${mins}m`;
  if (mins) return `${mins}m ${secs}s`;
  return `${secs}s`;
}

/**
 * Wall-clock parts for an IANA time zone, computed in the browser so a clock
 * can tick locally without polling the server.
 */
export function clockInZone(tz: string, date = new Date()): { time: string; date: string; zone: string } {
  const safeTz = tz || 'UTC';
  const opts = (extra: Intl.DateTimeFormatOptions) => {
    try {
      return new Intl.DateTimeFormat(undefined, { timeZone: safeTz, ...extra });
    } catch {
      return new Intl.DateTimeFormat(undefined, extra);
    }
  };
  const time = opts({ hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(date);
  const day = opts({ weekday: 'short', year: 'numeric', month: 'short', day: '2-digit' }).format(date);
  let zone = safeTz;
  try {
    const parts = new Intl.DateTimeFormat(undefined, { timeZone: safeTz, timeZoneName: 'short' }).formatToParts(date);
    zone = parts.find((p) => p.type === 'timeZoneName')?.value ?? safeTz;
  } catch {
    /* keep the raw zone id */
  }
  return { time, date: day, zone };
}
