import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, RefreshCcw, Trash2, Zap } from 'lucide-react';
import { api } from '../../api/client';
import { ConnectorDescriptor, Integration } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';
import { categoryVisual, connectorVisual } from './connectorMeta';

interface Form {
  id: number | null;
  name: string;
  kind: string;
  enabled: boolean;
  base_url: string;
  username: string;
  secret: string;
  verify_tls: boolean;
  settings: Record<string, string>;
}

const empty = (kind = ''): Form => ({
  id: null, name: '', kind, enabled: true, base_url: '', username: '', secret: '',
  verify_tls: true, settings: {},
});

export default function Integrations() {
  const toast = useToast();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [form, setForm] = useState<Form>(empty());
  const [deleting, setDeleting] = useState<Integration | null>(null);

  const { data: catalog = [] } = useQuery({
    queryKey: ['integration-catalog'],
    queryFn: () => api.get<ConnectorDescriptor[]>('/api/v1/integrations/catalog'),
  });
  const { data: integrations = [], refetch } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.get<Integration[]>('/api/v1/integrations'),
  });

  const descriptor = useMemo(
    () => catalog.find((c) => c.kind === form.kind),
    [catalog, form.kind],
  );

  const save = useMutation({
    mutationFn: (f: Form) => {
      const body = {
        name: f.name, kind: f.kind, enabled: f.enabled, base_url: f.base_url,
        username: f.username, secret: f.secret, verify_tls: f.verify_tls, settings: f.settings,
      };
      return f.id ? api.patch(`/api/v1/integrations/${f.id}`, body) : api.post('/api/v1/integrations', body);
    },
    onSuccess: () => {
      toast('success', form.id ? 'Integration updated' : 'Integration created');
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['integrations'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const test = useMutation({
    mutationFn: (i: Integration) => api.post<{ ok: boolean; message: string }>(`/api/v1/integrations/${i.id}/test`),
    onSuccess: (r) => {
      toast(r.ok ? 'success' : 'error', r.message);
      qc.invalidateQueries({ queryKey: ['integrations'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const sync = useMutation({
    mutationFn: (i: Integration) => api.post<{ ok: boolean; detail: string; message: string }>(`/api/v1/integrations/${i.id}/sync`),
    onSuccess: (r) => {
      toast(r.ok ? 'success' : 'error', r.detail || r.message);
      qc.invalidateQueries({ queryKey: ['integrations'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (i: Integration) => api.delete(`/api/v1/integrations/${i.id}`),
    onSuccess: () => {
      toast('success', 'Integration deleted');
      setDeleting(null);
      qc.invalidateQueries({ queryKey: ['integrations'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const startCreate = (kind: string) => {
    const d = catalog.find((c) => c.kind === kind);
    const settings: Record<string, string> = {};
    d?.fields.forEach((f) => { if (f.default) settings[f.key] = f.default; });
    setForm({ ...empty(kind), settings });
    setShowAdvanced(false);
    setOpen(true);
  };

  const edit = (i: Integration) => {
    setForm({
      id: i.id, name: i.name, kind: i.kind, enabled: i.enabled, base_url: i.base_url,
      username: i.username, secret: '', verify_tls: i.verify_tls, settings: { ...i.settings },
    });
    setShowAdvanced(false);
    setOpen(true);
  };

  const setSetting = (key: string, value: string) =>
    setForm({ ...form, settings: { ...form.settings, [key]: value } });

  const categories = useMemo(() => {
    const grouped = new Map<string, ConnectorDescriptor[]>();
    for (const c of catalog) {
      const list = grouped.get(c.category) ?? [];
      list.push(c);
      grouped.set(c.category, list);
    }
    return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [catalog]);

  return (
    <>
      <h1 className="text-lg font-semibold mb-1">Integrations</h1>
      <p className="text-table text-muted mb-3">
        Connect M-Eyes to your Fortinet and Microsoft estate. Connectors import networks and
        devices into IPAM and the asset inventory, push objects out, and feed the automation
        engine for hands-off, scheduled synchronisation.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-4">
        {categories.map(([category, items]) => {
          const cat = categoryVisual(category);
          return (
            <div key={category} className="f-card overflow-hidden">
              <div
                className="flex items-center gap-2 px-3 py-2.5 border-b border-line"
                style={{ background: cat.tint }}
              >
                <cat.Brand />
                <span className="font-semibold text-sm" style={{ color: cat.color }}>
                  {cat.label}
                </span>
                <span className="ml-auto text-xs text-muted">
                  {items.length} connector{items.length === 1 ? '' : 's'}
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-3">
                {items.map((c) => {
                  const v = connectorVisual(c.kind);
                  return (
                    <button
                      key={c.kind}
                      onClick={() => startCreate(c.kind)}
                      title={`Add ${c.label}`}
                      className="group flex items-start gap-2.5 p-2.5 rounded-lg border border-line bg-white text-left transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-slate-300"
                    >
                      <span
                        className="shrink-0 w-9 h-9 rounded-lg grid place-items-center transition-transform group-hover:scale-105"
                        style={{ background: `${v.color}14`, color: v.color, border: `1px solid ${v.color}33` }}
                      >
                        <v.Icon size={18} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium text-table truncate">{c.label}</span>
                        <span
                          className="block text-[11px] text-muted leading-snug"
                          style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                        >
                          {c.description}
                        </span>
                      </span>
                      <Plus
                        size={15}
                        className="ml-auto shrink-0 text-muted opacity-0 group-hover:opacity-100 transition-opacity"
                        style={{ color: v.color }}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <DataTable
        columns={[
          {
            header: 'Name',
            searchText: (i: Integration) => i.name,
            render: (i) => {
              const v = connectorVisual(i.kind);
              return (
                <span className="inline-flex items-center gap-2 font-medium">
                  <span
                    className="shrink-0 w-6 h-6 rounded grid place-items-center"
                    style={{ background: `${v.color}14`, color: v.color, border: `1px solid ${v.color}33` }}
                  >
                    <v.Icon size={13} />
                  </span>
                  {i.name}
                </span>
              );
            },
          },
          { header: 'Kind', render: (i) => <span className="text-xs">{catalog.find((c) => c.kind === i.kind)?.label ?? i.kind}</span> },
          { header: 'Enabled', render: (i) => <StatusBadge value={i.enabled ? 'used' : 'free'} /> },
          { header: 'Status', render: (i) => <StatusBadge value={i.last_status === 'ok' ? 'success' : i.last_status === 'error' ? 'failed' : 'free'} /> },
          { header: 'Last result', searchText: (i: Integration) => i.last_message, render: (i) => <span className="text-xs text-muted">{i.last_message || '—'}</span> },
          {
            header: 'Actions',
            render: (i) => (
              <div className="flex gap-2 items-center">
                <button onClick={() => test.mutate(i)} className="text-accent hover:opacity-70 text-xs flex items-center gap-1" title="Test connection">
                  <Zap size={13} /> Test
                </button>
                <button onClick={() => sync.mutate(i)} className="text-accent hover:opacity-70 text-xs flex items-center gap-1" title="Run sync">
                  <RefreshCcw size={13} /> Sync
                </button>
                <button onClick={() => edit(i)} className="text-accent hover:opacity-70 text-xs">Edit</button>
                <button onClick={() => setDeleting(i)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            ),
          },
        ]}
        rows={integrations}
        rowKey={(i) => i.id}
        onRefresh={() => refetch()}
        emptyText="No integrations configured yet — pick a connector above."
      />

      <SlideOver title={form.id ? `Edit ${form.name}` : `New ${descriptor?.label ?? ''} integration`} open={open} onClose={() => setOpen(false)}>
        {descriptor && <p className="text-xs text-muted mb-3">{descriptor.description}</p>}
        <FormField label="Name">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="edge-firewall" />
        </FormField>
        {descriptor?.uses_base_url && (
          <FormField label={descriptor.base_url_label}>
            <input className="f-input font-mono" value={form.base_url} placeholder={descriptor.base_url_placeholder}
                   onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
          </FormField>
        )}
        {descriptor?.uses_username && (
          <FormField label={descriptor.username_label}>
            <input className="f-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </FormField>
        )}
        {descriptor?.uses_secret && (
          <FormField label={descriptor.secret_label} hint={form.id ? 'Leave blank to keep the stored secret' : ''}>
            <input className="f-input font-mono" type="password" value={form.secret}
                   onChange={(e) => setForm({ ...form, secret: e.target.value })} />
          </FormField>
        )}

        {descriptor?.fields.filter((f) => !f.advanced).map((f) => (
          <FieldInput key={f.key} field={f} value={form.settings[f.key] ?? ''} onChange={(v) => setSetting(f.key, v)} />
        ))}

        {descriptor && descriptor.fields.some((f) => f.advanced) && (
          <button className="text-accent text-xs mb-2" onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? 'Hide' : 'Show'} advanced settings
          </button>
        )}
        {showAdvanced && descriptor?.fields.filter((f) => f.advanced).map((f) => (
          <FieldInput key={f.key} field={f} value={form.settings[f.key] ?? ''} onChange={(v) => setSetting(f.key, v)} />
        ))}

        <div className="grid grid-cols-2 gap-2 mt-2">
          <label className="flex items-center gap-2 text-table">
            <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled
          </label>
          <label className="flex items-center gap-2 text-table">
            <input type="checkbox" checked={form.verify_tls} onChange={(e) => setForm({ ...form, verify_tls: e.target.checked })} /> Verify TLS
          </label>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={save.isPending || !form.name || !form.kind} onClick={() => save.mutate(form)}>
            {form.id ? 'Save' : 'Create'}
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete integration"
        message={`Delete ${deleting?.name}? Stored credentials will be removed.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}

function FieldInput({ field, value, onChange }: { field: ConnectorDescriptor['fields'][number]; value: string; onChange: (v: string) => void }) {
  if (field.type === 'bool') {
    return (
      <label className="flex items-center gap-2 text-table mb-3">
        <input type="checkbox" checked={value === 'true'} onChange={(e) => onChange(e.target.checked ? 'true' : 'false')} />
        {field.label}
      </label>
    );
  }
  return (
    <FormField label={field.label} hint={field.help}>
      <input
        className="f-input"
        type={field.type === 'number' ? 'number' : 'text'}
        value={value}
        placeholder={field.placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </FormField>
  );
}
