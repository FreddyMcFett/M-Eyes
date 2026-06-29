import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { api } from '../api/client';
import { AppEvent } from '../api/types';
import StatusBadge from '../components/StatusBadge';
import { useToast } from '../components/Toast';
import { useEventStream } from '../hooks/useEventStream';

const SEVERITIES = ['', 'debug', 'info', 'warning', 'error'];
const CATEGORIES = ['', 'auth', 'ipam', 'dns', 'dhcp', 'deploy', 'feeds', 'system'];

export default function Events() {
  const toast = useToast();
  const [severity, setSeverity] = useState('');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [liveTail, setLiveTail] = useState(true);
  const [exporting, setExporting] = useState(false);

  const liveEvents = useEventStream(100, liveTail);

  const exportLog = async () => {
    const params = new URLSearchParams();
    if (severity) params.set('severity', severity);
    if (category) params.set('category', category);
    if (search) params.set('search', search);
    const qs = params.toString();
    setExporting(true);
    try {
      await api.download(`/api/v1/events/export${qs ? `?${qs}` : ''}`, 'm-eyes-events.log');
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const { data: events = [], refetch } = useQuery({
    queryKey: ['events', severity, category, search],
    queryFn: () => {
      const params = new URLSearchParams({ limit: '200' });
      if (severity) params.set('severity', severity);
      if (category) params.set('category', category);
      if (search) params.set('search', search);
      return api.get<AppEvent[]>(`/api/v1/events?${params}`);
    },
    refetchInterval: liveTail ? 5000 : false,
  });

  // merge live events on top (avoid duplicates by id)
  const known = new Set(events.map((e) => e.id));
  const merged = [
    ...liveEvents
      .filter((e) => !known.has(e.id))
      .filter((e) => !severity || e.severity === severity)
      .filter((e) => !category || e.category === category)
      .filter((e) => !search || e.message.toLowerCase().includes(search.toLowerCase()))
      .map((e) => ({ ...e, data: null })),
    ...events,
  ];

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">Log &amp; Report — Events</h1>
      <div className="f-card">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-line flex-wrap">
          <select className="f-input w-32" value={severity} onChange={(e) => setSeverity(e.target.value)}>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s || 'all severities'}</option>)}
          </select>
          <select className="f-input w-32" value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c || 'all categories'}</option>)}
          </select>
          <input className="f-input w-56" placeholder="Search messages" value={search} onChange={(e) => setSearch(e.target.value)} />
          <label className="flex items-center gap-1.5 text-table ml-auto">
            <input type="checkbox" checked={liveTail} onChange={(e) => setLiveTail(e.target.checked)} />
            Live tail
            {liveTail && <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />}
          </label>
          <button className="f-btn-secondary" onClick={exportLog} disabled={exporting} title="Download the filtered log as a .log file">
            <Download size={14} /> {exporting ? 'Exporting…' : 'Export .log'}
          </button>
          <button className="f-btn-secondary" onClick={() => refetch()}>Refresh</button>
        </div>
        <table className="f-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Severity</th>
              <th>Category</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {merged.map((event) => (
              <tr key={event.id}>
                <td className="whitespace-nowrap font-mono text-xs">{new Date(event.ts).toLocaleString()}</td>
                <td><StatusBadge value={event.severity} /></td>
                <td>{event.category}</td>
                <td>{event.message}</td>
              </tr>
            ))}
            {merged.length === 0 && (
              <tr><td colSpan={4} className="text-center text-muted py-6">No events</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
