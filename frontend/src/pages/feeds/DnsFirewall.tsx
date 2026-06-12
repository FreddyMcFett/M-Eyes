import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileCode2, RefreshCw, Trash2, UploadCloud } from 'lucide-react';
import { api } from '../../api/client';
import { RpzRule, ThreatFeed } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

const ACTIONS = ['block', 'nodata', 'passthru', 'substitute'];

interface RuleForm {
  fqdn: string;
  action: string;
  substitute: string;
  comment: string;
}

const EMPTY: RuleForm = { fqdn: '', action: 'block', substitute: '', comment: '' };

interface FeedForm {
  name: string;
  url: string;
  action: string;
  refresh_hours: string;
}

const EMPTY_FEED: FeedForm = { name: '', url: '', action: 'block', refresh_hours: '24' };

export default function DnsFirewall() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [form, setForm] = useState<RuleForm>(EMPTY);
  const [deleting, setDeleting] = useState<RpzRule | null>(null);
  const [feedEditorOpen, setFeedEditorOpen] = useState(false);
  const [feedForm, setFeedForm] = useState<FeedForm>(EMPTY_FEED);
  const [deletingFeed, setDeletingFeed] = useState<ThreatFeed | null>(null);

  const { data: rules = [], refetch } = useQuery({
    queryKey: ['rpz-rules'],
    queryFn: () => api.get<RpzRule[]>('/api/v1/rpz/rules'),
  });
  const { data: feeds = [], refetch: refetchFeeds } = useQuery({
    queryKey: ['rpz-threat-feeds'],
    queryFn: () => api.get<ThreatFeed[]>('/api/v1/rpz/threat-feeds'),
  });
  const { data: preview } = useQuery({
    queryKey: ['rpz-preview', rules.length, rules],
    queryFn: () => api.get<{ zone: string; content: string }>('/api/v1/rpz/preview'),
    enabled: previewOpen,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['rpz-rules'] });

  const create = useMutation({
    mutationFn: () => api.post('/api/v1/rpz/rules', form),
    onSuccess: () => {
      toast('success', 'Rule created — deploy to BIND to activate');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const toggle = useMutation({
    mutationFn: (rule: RpzRule) => api.patch(`/api/v1/rpz/rules/${rule.id}`, { enabled: !rule.enabled }),
    onSuccess: () => invalidate(),
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (rule: RpzRule) => api.delete(`/api/v1/rpz/rules/${rule.id}`),
    onSuccess: () => {
      toast('success', 'Rule deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const deployBind = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>('/api/v1/deploy/bind'),
    onSuccess: (result) =>
      toast(result.status === 'success' ? 'success' : 'error', `BIND: ${result.detail}`),
    onError: (err: Error) => toast('error', err.message),
  });

  const invalidateFeeds = () => queryClient.invalidateQueries({ queryKey: ['rpz-threat-feeds'] });

  const createFeed = useMutation({
    mutationFn: () =>
      api.post<ThreatFeed>('/api/v1/rpz/threat-feeds', {
        name: feedForm.name,
        url: feedForm.url,
        action: feedForm.action,
        refresh_hours: Number(feedForm.refresh_hours) || 24,
      }),
    onSuccess: (feed) => {
      setFeedEditorOpen(false);
      invalidateFeeds();
      syncFeed.mutate(feed);
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const toggleFeed = useMutation({
    mutationFn: (feed: ThreatFeed) =>
      api.patch(`/api/v1/rpz/threat-feeds/${feed.id}`, { enabled: !feed.enabled }),
    onSuccess: () => invalidateFeeds(),
    onError: (err: Error) => toast('error', err.message),
  });

  const syncFeed = useMutation({
    mutationFn: (feed: ThreatFeed) => api.post<ThreatFeed>(`/api/v1/rpz/threat-feeds/${feed.id}/sync`),
    onSuccess: (feed) => {
      toast(
        feed.last_status.startsWith('ok') ? 'success' : 'error',
        `${feed.name}: ${feed.last_status} — deploy to BIND to activate`,
      );
      invalidateFeeds();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const removeFeed = useMutation({
    mutationFn: (feed: ThreatFeed) => api.delete(`/api/v1/rpz/threat-feeds/${feed.id}`),
    onSuccess: () => {
      toast('success', 'Threat feed deleted');
      setDeletingFeed(null);
      invalidateFeeds();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">Security Fabric — DNS Firewall</h1>
      <p className="text-table text-muted mb-3 max-w-3xl">
        Domain rules are published to BIND as a Response Policy Zone (RPZ). Every rule covers the
        domain and all its subdomains; deploy to BIND to activate changes.
      </p>
      <DataTable
        columns={[
          { header: 'Domain', searchText: (r: RpzRule) => r.fqdn, render: (r) => <span className="font-mono">{r.fqdn}</span> },
          { header: 'Action', searchText: (r: RpzRule) => r.action, render: (r) => <StatusBadge value={r.action} /> },
          { header: 'Substitute', render: (r) => <span className="font-mono">{r.substitute || '—'}</span> },
          { header: 'Comment', searchText: (r: RpzRule) => r.comment, render: (r) => <span>{r.comment || '—'}</span> },
          {
            header: 'Enabled',
            render: (r) => (
              <input type="checkbox" checked={r.enabled} onChange={() => toggle.mutate(r)} />
            ),
          },
          {
            header: 'Actions',
            render: (r) => (
              <button onClick={() => setDeleting(r)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={rules}
        rowKey={(r) => r.id}
        onCreate={() => {
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Add Rule"
        onRefresh={() => refetch()}
        emptyText="No DNS firewall rules"
        toolbar={
          <>
            <button className="f-btn-secondary" onClick={() => setPreviewOpen(true)}>
              <FileCode2 size={14} /> Preview RPZ zone
            </button>
            <button className="f-btn-secondary" disabled={deployBind.isPending} onClick={() => deployBind.mutate()}>
              <UploadCloud size={14} /> Deploy to BIND
            </button>
          </>
        }
      />

      <h2 className="text-base font-semibold mt-6 mb-2">Threat Intelligence Feeds</h2>
      <p className="text-table text-muted mb-3 max-w-3xl">
        External domain blocklists (plain list or hosts-file format) merged into the RPZ zone.
        Feeds re-sync automatically on their refresh interval; manual rules always take
        precedence, so a passthru rule whitelists a feed entry.
      </p>
      <DataTable
        columns={[
          { header: 'Name', searchText: (f: ThreatFeed) => f.name, render: (f) => <span className="font-medium">{f.name}</span> },
          { header: 'URL', searchText: (f: ThreatFeed) => f.url, render: (f) => <span className="font-mono text-xs break-all">{f.url}</span> },
          { header: 'Action', render: (f) => <StatusBadge value={f.action} /> },
          { header: 'Entries', render: (f) => <span className="font-mono">{f.entry_count}</span> },
          {
            header: 'Last sync',
            render: (f) => (
              <span title={f.last_status} className={f.last_status.startsWith('ok') || !f.last_status ? '' : 'text-danger'}>
                {f.last_synced ? new Date(f.last_synced).toLocaleString() : 'never'}
              </span>
            ),
          },
          { header: 'Refresh', render: (f) => <span>{f.refresh_hours}h</span> },
          {
            header: 'Enabled',
            render: (f) => <input type="checkbox" checked={f.enabled} onChange={() => toggleFeed.mutate(f)} />,
          },
          {
            header: 'Actions',
            render: (f) => (
              <span className="flex gap-2">
                <button onClick={() => syncFeed.mutate(f)} className="text-info hover:opacity-70" title="Sync now" disabled={syncFeed.isPending}>
                  <RefreshCw size={14} />
                </button>
                <button onClick={() => setDeletingFeed(f)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </span>
            ),
          },
        ]}
        rows={feeds}
        rowKey={(f) => f.id}
        onCreate={() => {
          setFeedForm(EMPTY_FEED);
          setFeedEditorOpen(true);
        }}
        createLabel="Add Feed"
        onRefresh={() => refetchFeeds()}
        emptyText="No threat intelligence feeds"
      />

      <SlideOver title="Add threat intelligence feed" open={feedEditorOpen} onClose={() => setFeedEditorOpen(false)}>
        <FormField label="Name">
          <input className="f-input" value={feedForm.name} onChange={(e) => setFeedForm({ ...feedForm, name: e.target.value })} placeholder="URLhaus malware domains" />
        </FormField>
        <FormField label="Feed URL" hint="Plain domain list or hosts-file format; comments with # or ;">
          <input className="f-input font-mono" value={feedForm.url} onChange={(e) => setFeedForm({ ...feedForm, url: e.target.value })} placeholder="https://urlhaus.abuse.ch/downloads/hostfile/" />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Action" hint="block = NXDOMAIN · nodata = empty answer">
            <select className="f-input" value={feedForm.action} onChange={(e) => setFeedForm({ ...feedForm, action: e.target.value })}>
              <option value="block">block</option>
              <option value="nodata">nodata</option>
            </select>
          </FormField>
          <FormField label="Refresh interval (hours)">
            <input className="f-input" type="number" min={1} max={168} value={feedForm.refresh_hours} onChange={(e) => setFeedForm({ ...feedForm, refresh_hours: e.target.value })} />
          </FormField>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setFeedEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={createFeed.isPending || !feedForm.name || !feedForm.url}
            onClick={() => createFeed.mutate()}
          >
            Add & sync
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete threat feed"
        message={`Delete the feed ${deletingFeed?.name} and its ${deletingFeed?.entry_count ?? 0} cached entries?`}
        open={deletingFeed !== null}
        onCancel={() => setDeletingFeed(null)}
        onConfirm={() => deletingFeed && removeFeed.mutate(deletingFeed)}
      />

      <SlideOver title="Add DNS firewall rule" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="Domain" hint="Covers the domain and all subdomains, e.g. malware.example.com">
          <input className="f-input font-mono" value={form.fqdn} onChange={(e) => setForm({ ...form, fqdn: e.target.value })} />
        </FormField>
        <FormField label="Action" hint="block = NXDOMAIN · nodata = empty answer · passthru = whitelist · substitute = redirect">
          <select className="f-input" value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })}>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </FormField>
        {form.action === 'substitute' && (
          <FormField label="Substitute" hint="Replacement IP address or FQDN (walled garden)">
            <input className="f-input font-mono" value={form.substitute} onChange={(e) => setForm({ ...form, substitute: e.target.value })} />
          </FormField>
        )}
        <FormField label="Comment">
          <input className="f-input" value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={create.isPending || !form.fqdn || (form.action === 'substitute' && !form.substitute)}
            onClick={() => create.mutate()}
          >
            Add
          </button>
        </div>
      </SlideOver>

      <Modal title={`RPZ zone preview — ${preview?.zone ?? ''}`} open={previewOpen} onClose={() => setPreviewOpen(false)}>
        <pre className="text-xs font-mono bg-slate-900 text-slate-100 p-3 rounded overflow-x-auto max-h-[60vh]">
          {preview?.content ?? 'Loading…'}
        </pre>
      </Modal>

      <ConfirmDialog
        title="Delete rule"
        message={`Delete the DNS firewall rule for ${deleting?.fqdn}?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
