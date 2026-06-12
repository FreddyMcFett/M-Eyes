import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { BlocklistEntry } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import { useToast } from '../../components/Toast';

export default function Blocklist() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState({ value: '', reason: '' });
  const [deleting, setDeleting] = useState<BlocklistEntry | null>(null);

  const { data: entries = [], refetch } = useQuery({
    queryKey: ['blocklist'],
    queryFn: () => api.get<BlocklistEntry[]>('/api/v1/blocklist'),
  });

  const create = useMutation({
    mutationFn: () => api.post('/api/v1/blocklist', form),
    onSuccess: () => {
      toast('success', 'Entry blocklisted — FortiGates pick it up on next feed refresh');
      setEditorOpen(false);
      queryClient.invalidateQueries({ queryKey: ['blocklist'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (entry: BlocklistEntry) => api.delete(`/api/v1/blocklist/${entry.id}`),
    onSuccess: () => {
      toast('success', 'Entry removed');
      setDeleting(null);
      queryClient.invalidateQueries({ queryKey: ['blocklist'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">Security Fabric — Blocklist</h1>
      <p className="text-table text-muted mb-3 max-w-3xl">
        IPs and CIDRs listed here are published through the blocklist feed; FortiGates consuming the
        feed as an External Resource can block them in firewall policies.
      </p>
      <DataTable
        columns={[
          { header: 'IP / CIDR', searchText: (e: BlocklistEntry) => e.value, render: (e) => <span className="font-mono">{e.value}</span> },
          { header: 'Reason', searchText: (e: BlocklistEntry) => e.reason, render: (e) => <span>{e.reason || '—'}</span> },
          { header: 'Added by', render: (e) => <span>{e.created_by}</span> },
          { header: 'Added', render: (e) => <span>{new Date(e.created_at).toLocaleString()}</span> },
          {
            header: 'Actions',
            render: (e) => (
              <button onClick={() => setDeleting(e)} className="text-danger hover:opacity-70">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={entries}
        rowKey={(e) => e.id}
        onCreate={() => {
          setForm({ value: '', reason: '' });
          setEditorOpen(true);
        }}
        createLabel="Block address"
        onRefresh={() => refetch()}
      />

      <SlideOver title="Block address" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="IP or CIDR" hint="e.g. 203.0.113.7 or 198.51.100.0/24">
          <input className="f-input font-mono" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
        </FormField>
        <FormField label="Reason">
          <input className="f-input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={!form.value || create.isPending} onClick={() => create.mutate()}>
            Block
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Remove from blocklist"
        message={`Stop blocking ${deleting?.value}?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
