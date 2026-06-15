import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Pencil, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { DnsView } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import { useToast } from '../../components/Toast';

interface ViewForm {
  name: string;
  match_clients: string;
  description: string;
  position: string;
}

const EMPTY: ViewForm = { name: '', match_clients: 'any', description: '', position: '0' };

export default function Views() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<DnsView | null>(null);
  const [form, setForm] = useState<ViewForm>(EMPTY);
  const [deleting, setDeleting] = useState<DnsView | null>(null);

  const { data: views = [], refetch } = useQuery({
    queryKey: ['dns-views'],
    queryFn: () => api.get<DnsView[]>('/api/v1/views'),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['dns-views'] });

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        match_clients: form.match_clients,
        description: form.description,
        position: Number(form.position) || 0,
      };
      return editing
        ? api.patch(`/api/v1/views/${editing.id}`, payload)
        : api.post('/api/v1/views', { ...payload, name: form.name });
    },
    onSuccess: () => {
      toast('success', editing ? 'View updated' : 'View created');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (view: DnsView) => api.delete(`/api/v1/views/${view.id}`),
    onSuccess: () => {
      toast('success', 'View deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">DNS — Views</h1>
      <p className="text-table text-muted mb-3 max-w-3xl">
        Split-horizon DNS: the DNS engine matches clients against views in order; zones without a view
        land in the implicit catch-all <span className="font-mono">default</span> view, evaluated last.
      </p>
      <DataTable
        columns={[
          { header: 'View', searchText: (v: DnsView) => v.name, render: (v) => <span className="font-mono">{v.name}</span> },
          { header: 'Match clients', searchText: (v: DnsView) => v.match_clients, render: (v) => <span className="font-mono">{v.match_clients}</span> },
          { header: 'Order', render: (v) => <span>{v.position}</span> },
          { header: 'Zones', render: (v) => <span>{v.zone_count}</span> },
          { header: 'Description', searchText: (v: DnsView) => v.description, render: (v) => <span>{v.description || '—'}</span> },
          {
            header: 'Actions',
            render: (v) => (
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setEditing(v);
                    setForm({ name: v.name, match_clients: v.match_clients, description: v.description, position: String(v.position) });
                    setEditorOpen(true);
                  }}
                  className="text-info hover:opacity-70"
                  title="Edit"
                >
                  <Pencil size={14} />
                </button>
                <button onClick={() => setDeleting(v)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            ),
          },
        ]}
        rows={views}
        rowKey={(v) => v.id}
        onCreate={() => {
          setEditing(null);
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Create View"
        onRefresh={() => refetch()}
        emptyText="No views: all zones are served identically to every client"
      />

      <SlideOver title={editing ? `Edit view ${editing.name}` : 'Create View'} open={editorOpen} onClose={() => setEditorOpen(false)}>
        {!editing && (
          <FormField label="Name" hint="e.g. internal, external, guest">
            <input className="f-input font-mono" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </FormField>
        )}
        <FormField label="Match clients" hint="Comma-separated: any, none, localhost, localnets, CIDRs (prefix ! to negate)">
          <input className="f-input font-mono" value={form.match_clients} onChange={(e) => setForm({ ...form, match_clients: e.target.value })} />
        </FormField>
        <FormField label="Evaluation order" hint="Lowest first; the default view always matches last">
          <input className="f-input" type="number" value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
        </FormField>
        <FormField label="Description">
          <input className="f-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={save.isPending || (!editing && !form.name) || !form.match_clients}
            onClick={() => save.mutate()}
          >
            {editing ? 'Save' : 'Create'}
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete view"
        message={`Delete view ${deleting?.name}? Zones must be moved out first.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
