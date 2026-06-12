import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { ChangeLogEntry } from '../api/types';
import ConfirmDialog from '../components/ConfirmDialog';
import DiffViewer from '../components/DiffViewer';
import SlideOver from '../components/SlideOver';
import StatusBadge from '../components/StatusBadge';
import { useToast } from '../components/Toast';

const OBJECT_TYPES = ['', 'network', 'ip_address', 'zone', 'record', 'dhcp_subnet', 'dhcp_range',
  'dhcp_reservation', 'dhcp_option', 'host', 'feed', 'blocklist_entry', 'tag'];

export default function Changelog() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [objectType, setObjectType] = useState('');
  const [selected, setSelected] = useState<ChangeLogEntry | null>(null);
  const [confirmRollback, setConfirmRollback] = useState(false);

  const { data: entries = [], refetch } = useQuery({
    queryKey: ['changelog', objectType],
    queryFn: () =>
      api.get<ChangeLogEntry[]>(`/api/v1/changelog?limit=100${objectType ? `&object_type=${objectType}` : ''}`),
    refetchInterval: 10000,
  });

  const rollback = useMutation({
    mutationFn: (entry: ChangeLogEntry) => api.post(`/api/v1/changelog/${entry.id}/rollback`),
    onSuccess: () => {
      toast('success', 'Change rolled back (recorded as a new change)');
      setConfirmRollback(false);
      setSelected(null);
      queryClient.invalidateQueries();
    },
    onError: (err: Error) => {
      toast('error', err.message);
      setConfirmRollback(false);
    },
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">Log &amp; Report — Change Log</h1>
      <div className="f-card">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-line">
          <label className="text-table text-muted">Object type</label>
          <select className="f-input w-48" value={objectType} onChange={(e) => setObjectType(e.target.value)}>
            {OBJECT_TYPES.map((t) => (
              <option key={t} value={t}>{t || 'all'}</option>
            ))}
          </select>
          <button className="f-btn-secondary ml-auto" onClick={() => refetch()}>Refresh</button>
        </div>
        <table className="f-table">
          <thead>
            <tr>
              <th>Version</th>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Object</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id} className="cursor-pointer" onClick={() => setSelected(entry)}>
                <td className="font-mono text-xs">v{entry.id}</td>
                <td className="whitespace-nowrap">{new Date(entry.ts).toLocaleString()}</td>
                <td>{entry.actor}</td>
                <td><StatusBadge value={entry.action} /></td>
                <td>{entry.object_type} #{entry.object_id}</td>
                <td>{entry.summary}</td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr><td colSpan={6} className="text-center text-muted py-6">No changes recorded</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <SlideOver
        title={selected ? `Change v${selected.id} — ${selected.action} ${selected.object_type}` : ''}
        open={selected !== null}
        onClose={() => setSelected(null)}
      >
        {selected && (
          <>
            <div className="text-table text-muted mb-3">
              {new Date(selected.ts).toLocaleString()} by <strong>{selected.actor}</strong>
            </div>
            <DiffViewer before={selected.before} after={selected.after} />
            {selected.action !== 'rollback' && (
              <button className="f-btn-danger mt-4" onClick={() => setConfirmRollback(true)}>
                Roll back this change
              </button>
            )}
          </>
        )}
      </SlideOver>

      <ConfirmDialog
        title="Roll back change"
        message={`Roll back change v${selected?.id}? The previous state is restored as a NEW change; history is never rewritten.`}
        open={confirmRollback}
        onCancel={() => setConfirmRollback(false)}
        onConfirm={() => selected && rollback.mutate(selected)}
      />
    </>
  );
}
