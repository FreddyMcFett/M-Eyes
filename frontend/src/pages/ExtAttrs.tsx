import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { ExtAttrDef } from '../api/types';
import DataTable from '../components/DataTable';
import ConfirmDialog from '../components/ConfirmDialog';
import FormField from '../components/FormField';
import SlideOver from '../components/SlideOver';
import StatusBadge from '../components/StatusBadge';
import { useToast } from '../components/Toast';

const TYPES = ['string', 'integer', 'email', 'url', 'date', 'enum'];

interface DefForm {
  name: string;
  type: string;
  comment: string;
  allowed_values: string;
}

const EMPTY: DefForm = { name: '', type: 'string', comment: '', allowed_values: '' };

export default function ExtAttrs() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState<DefForm>(EMPTY);
  const [deleting, setDeleting] = useState<ExtAttrDef | null>(null);

  const { data: defs = [], refetch } = useQuery({
    queryKey: ['extattr-defs'],
    queryFn: () => api.get<ExtAttrDef[]>('/api/v1/extattr-defs'),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['extattr-defs'] });

  const create = useMutation({
    mutationFn: () =>
      api.post('/api/v1/extattr-defs', {
        name: form.name,
        type: form.type,
        comment: form.comment,
        allowed_values:
          form.type === 'enum'
            ? form.allowed_values.split(',').map((v) => v.trim()).filter(Boolean)
            : null,
      }),
    onSuccess: () => {
      toast('success', 'Attribute defined');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (def: ExtAttrDef) => api.delete(`/api/v1/extattr-defs/${def.id}`),
    onSuccess: () => {
      toast('success', 'Attribute deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">System — Extensible Attributes</h1>
      <p className="text-table text-muted mb-3 max-w-3xl">
        Typed metadata fields that can be attached to networks, IPs, zones, records and hosts —
        edit values on each object's detail page.
      </p>
      <DataTable
        columns={[
          { header: 'Name', searchText: (d: ExtAttrDef) => d.name, render: (d) => <span className="font-semibold">{d.name}</span> },
          { header: 'Type', searchText: (d: ExtAttrDef) => d.type, render: (d) => <StatusBadge value={d.type} /> },
          {
            header: 'Allowed values',
            render: (d) => <span className="font-mono">{d.allowed_values?.join(', ') || '—'}</span>,
          },
          { header: 'Comment', searchText: (d: ExtAttrDef) => d.comment, render: (d) => <span>{d.comment || '—'}</span> },
          { header: 'In use', render: (d) => <span>{d.usage_count}</span> },
          {
            header: 'Actions',
            render: (d) => (
              <button onClick={() => setDeleting(d)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={defs}
        rowKey={(d) => d.id}
        onCreate={() => {
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Define Attribute"
        onRefresh={() => refetch()}
        emptyText="No extensible attributes defined"
      />

      <SlideOver title="Define extensible attribute" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="Name" hint="e.g. Owner, Environment, Cost Center">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="Type">
          <select className="f-input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            {TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </FormField>
        {form.type === 'enum' && (
          <FormField label="Allowed values" hint="Comma-separated, e.g. prod, staging, dev">
            <input className="f-input" value={form.allowed_values} onChange={(e) => setForm({ ...form, allowed_values: e.target.value })} />
          </FormField>
        )}
        <FormField label="Comment">
          <input className="f-input" value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={create.isPending || !form.name || (form.type === 'enum' && !form.allowed_values)}
            onClick={() => create.mutate()}
          >
            Define
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete attribute"
        message={`Delete ${deleting?.name}? Its ${deleting?.usage_count ?? 0} value(s) on objects will be removed too.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
