import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Play, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { AutomationRule, Integration, Network } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

interface Form {
  id: number | null;
  name: string;
  kind: string;
  enabled: boolean;
  interval_seconds: number;
  config: Record<string, unknown>;
}

const empty = (): Form => ({ id: null, name: '', kind: 'asset_reconcile', enabled: true, interval_seconds: 3600, config: {} });

const KIND_LABELS: Record<string, string> = {
  discovery_sweep: 'Discovery sweep + asset reconcile',
  asset_reconcile: 'Asset reconcile from IPAM',
  integration_sync: 'Run an integration sync',
  auto_deploy: 'Auto-deploy pending DNS/DHCP config',
  threat_feed_sync: 'Refresh DNS-firewall threat feeds',
};

const INTERVALS = [
  [300, 'Every 5 minutes'], [900, 'Every 15 minutes'], [3600, 'Hourly'],
  [21600, 'Every 6 hours'], [86400, 'Daily'], [604800, 'Weekly'],
] as const;

function humanInterval(s: number) {
  const found = INTERVALS.find(([v]) => v === s);
  return found ? found[1] : `${s}s`;
}

export default function Automation() {
  const toast = useToast();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Form>(empty());
  const [deleting, setDeleting] = useState<AutomationRule | null>(null);

  const { data: rules = [], refetch } = useQuery({
    queryKey: ['automation'],
    queryFn: () => api.get<AutomationRule[]>('/api/v1/automation'),
  });
  const { data: kinds } = useQuery({
    queryKey: ['automation-kinds'],
    queryFn: () => api.get<{ kinds: string[] }>('/api/v1/automation/kinds'),
  });
  const { data: networks = [] } = useQuery({
    queryKey: ['networks'],
    queryFn: () => api.get<Network[]>('/api/v1/networks'),
  });
  const { data: integrations = [] } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.get<Integration[]>('/api/v1/integrations'),
  });

  const save = useMutation({
    mutationFn: (f: Form) => {
      const body = { name: f.name, kind: f.kind, enabled: f.enabled, interval_seconds: f.interval_seconds, config: f.config };
      return f.id ? api.patch(`/api/v1/automation/${f.id}`, body) : api.post('/api/v1/automation', body);
    },
    onSuccess: () => {
      toast('success', form.id ? 'Rule updated' : 'Rule created');
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['automation'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const run = useMutation({
    mutationFn: (r: AutomationRule) => api.post<{ status: string; message: string }>(`/api/v1/automation/${r.id}/run`),
    onSuccess: (r) => {
      toast(r.status === 'error' ? 'error' : 'success', `${r.status}: ${r.message}`);
      qc.invalidateQueries({ queryKey: ['automation'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (r: AutomationRule) => api.delete(`/api/v1/automation/${r.id}`),
    onSuccess: () => {
      toast('success', 'Rule deleted');
      setDeleting(null);
      qc.invalidateQueries({ queryKey: ['automation'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const edit = (r: AutomationRule) => {
    setForm({ id: r.id, name: r.name, kind: r.kind, enabled: r.enabled, interval_seconds: r.interval_seconds, config: { ...r.config } });
    setOpen(true);
  };

  const setConfig = (key: string, value: unknown) => setForm({ ...form, config: { ...form.config, [key]: value } });

  return (
    <>
      <h1 className="text-lg font-semibold mb-1">Automation</h1>
      <p className="text-table text-muted mb-3">
        Autonomous, scheduled tasks that keep M-Eyes self-driving: sweep networks and reconcile
        assets, run integration syncs, refresh threat feeds, and auto-deploy pending DNS/DHCP
        config when drift is detected. Every run is recorded in the event log and change history.
      </p>
      <DataTable
        columns={[
          { header: 'Name', searchText: (r: AutomationRule) => r.name, render: (r) => <span className="font-medium">{r.name}</span> },
          { header: 'Task', render: (r) => <span className="text-xs">{KIND_LABELS[r.kind] ?? r.kind}</span> },
          { header: 'Schedule', render: (r) => <span className="text-xs">{humanInterval(r.interval_seconds)}</span> },
          { header: 'Enabled', render: (r) => <StatusBadge value={r.enabled ? 'used' : 'free'} /> },
          { header: 'Last run', render: (r) => <StatusBadge value={r.last_status === 'ok' ? 'success' : r.last_status === 'error' ? 'failed' : r.last_status === 'skipped' ? 'unreachable' : 'free'} /> },
          { header: 'Result', searchText: (r: AutomationRule) => r.last_message, render: (r) => <span className="text-xs text-muted">{r.last_message || '—'}</span> },
          { header: 'Runs', render: (r) => <span className="text-xs">{r.run_count}</span> },
          {
            header: 'Actions',
            render: (r) => (
              <div className="flex gap-2 items-center">
                <button onClick={() => run.mutate(r)} className="text-accent hover:opacity-70 text-xs flex items-center gap-1" title="Run now">
                  <Play size={13} /> Run
                </button>
                <button onClick={() => edit(r)} className="text-accent hover:opacity-70 text-xs">Edit</button>
                <button onClick={() => setDeleting(r)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            ),
          },
        ]}
        rows={rules}
        rowKey={(r) => r.id}
        onCreate={() => { setForm(empty()); setOpen(true); }}
        createLabel="New Rule"
        onRefresh={() => refetch()}
      />

      <SlideOver title={form.id ? 'Edit rule' : 'New automation rule'} open={open} onClose={() => setOpen(false)}>
        <FormField label="Name">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="nightly-reconcile" />
        </FormField>
        <FormField label="Task">
          <select className="f-input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value, config: {} })}>
            {(kinds?.kinds ?? []).map((k) => <option key={k} value={k}>{KIND_LABELS[k] ?? k}</option>)}
          </select>
        </FormField>
        <FormField label="Schedule">
          <select className="f-input" value={form.interval_seconds} onChange={(e) => setForm({ ...form, interval_seconds: Number(e.target.value) })}>
            {INTERVALS.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
        </FormField>

        {form.kind === 'discovery_sweep' && (
          <FormField label="Network to sweep">
            <select className="f-input" value={String(form.config.network_id ?? '')} onChange={(e) => setConfig('network_id', Number(e.target.value))}>
              <option value="">— network —</option>
              {networks.filter((n) => !n.is_container).map((n) => <option key={n.id} value={n.id}>{n.cidr} {n.name && `(${n.name})`}</option>)}
            </select>
          </FormField>
        )}
        {form.kind === 'integration_sync' && (
          <FormField label="Integration">
            <select className="f-input" value={String(form.config.integration_id ?? '')} onChange={(e) => setConfig('integration_id', Number(e.target.value))}>
              <option value="">— integration —</option>
              {integrations.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </FormField>
        )}
        {form.kind === 'auto_deploy' && (
          <FormField label="Targets" hint="Deploys only when the live config lags the current version">
            <div className="flex gap-3">
              {['bind', 'kea'].map((t) => {
                const targets = (form.config.targets as string[]) ?? ['bind', 'kea'];
                return (
                  <label key={t} className="flex items-center gap-2 text-table">
                    <input type="checkbox" checked={targets.includes(t)} onChange={(e) => {
                      const next = e.target.checked ? [...new Set([...targets, t])] : targets.filter((x) => x !== t);
                      setConfig('targets', next);
                    }} /> {t.toUpperCase()}
                  </label>
                );
              })}
            </div>
          </FormField>
        )}

        <label className="flex items-center gap-2 text-table mt-2">
          <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /> Enabled
        </label>

        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={save.isPending || !form.name} onClick={() => save.mutate(form)}>
            {form.id ? 'Save' : 'Create'}
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete rule"
        message={`Delete automation rule ${deleting?.name}?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
