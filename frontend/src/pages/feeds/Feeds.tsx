import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, RefreshCcw, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { Feed, Tag } from '../../api/types';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

export default function Feeds() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState({ slug: '', name: '', kind: 'networks', tag_id: '' });
  const [deleting, setDeleting] = useState<Feed | null>(null);

  const { data: feeds = [] } = useQuery({
    queryKey: ['feeds'],
    queryFn: () => api.get<Feed[]>('/api/v1/feeds'),
  });
  const { data: tags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: () => api.get<Tag[]>('/api/v1/tags'),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['feeds'] });

  const create = useMutation({
    mutationFn: () =>
      api.post('/api/v1/feeds', {
        slug: form.slug,
        name: form.name || form.slug,
        kind: form.kind,
        tag_id: form.kind === 'tag' ? Number(form.tag_id) : null,
      }),
    onSuccess: () => {
      toast('success', 'Feed created');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const regenerate = useMutation({
    mutationFn: (feed: Feed) => api.post(`/api/v1/feeds/${feed.id}/regenerate-token`),
    onSuccess: () => {
      toast('success', 'Token regenerated — update your FortiGates');
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const toggle = useMutation({
    mutationFn: (feed: Feed) => api.patch(`/api/v1/feeds/${feed.id}`, { enabled: !feed.enabled }),
    onSuccess: () => invalidate(),
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (feed: Feed) => api.delete(`/api/v1/feeds/${feed.id}`),
    onSuccess: () => {
      toast('success', 'Feed deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const copy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast('success', `${label} copied to clipboard`);
  };

  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <h1 className="text-lg font-semibold">Security Fabric — Fortinet Feeds</h1>
        <button className="f-btn-primary ml-auto" onClick={() => { setForm({ slug: '', name: '', kind: 'networks', tag_id: '' }); setEditorOpen(true); }}>
          Create Feed
        </button>
      </div>
      <p className="text-table text-muted mb-4 max-w-3xl">
        Each feed is an HTTP endpoint that FortiGates consume natively as an{' '}
        <span className="font-semibold">External Resource</span> (Threat Feed). Point the FortiGate at the
        feed URL with username <code className="font-mono bg-slate-100 px-1 rounded">feed</code> and the
        feed token as password — entries refresh automatically. Use HTTPS in production.
      </p>

      <div className="space-y-4">
        {feeds.map((feed) => {
          const url = `${window.location.origin}/feeds/${feed.slug}.txt`;
          return (
            <div key={feed.id} className="f-card p-4">
              <div className="flex items-center gap-3 flex-wrap">
                <h3 className="font-semibold">{feed.name}</h3>
                <StatusBadge value={feed.kind} />
                <span className="text-xs text-muted">{feed.entry_count} entries</span>
                <label className="flex items-center gap-1.5 text-xs ml-auto">
                  <input type="checkbox" checked={feed.enabled} onChange={() => toggle.mutate(feed)} />
                  enabled
                </label>
                <button className="f-btn-secondary" onClick={() => regenerate.mutate(feed)} title="Regenerate token">
                  <RefreshCcw size={13} /> Rotate token
                </button>
                <button className="f-btn-danger" onClick={() => setDeleting(feed)} title="Delete feed">
                  <Trash2 size={13} />
                </button>
              </div>
              <div className="grid md:grid-cols-2 gap-3 mt-3">
                <div>
                  <div className="text-xs text-muted uppercase mb-1">Feed URL</div>
                  <div className="flex items-center gap-1">
                    <code className="flex-1 text-xs bg-slate-100 rounded px-2 py-1.5 font-mono truncate">{url}</code>
                    <button className="f-btn-secondary" onClick={() => copy(url, 'URL')}><Copy size={13} /></button>
                  </div>
                  <div className="text-xs text-muted uppercase mb-1 mt-2">Token</div>
                  <div className="flex items-center gap-1">
                    <code className="flex-1 text-xs bg-slate-100 rounded px-2 py-1.5 font-mono truncate">{feed.token}</code>
                    <button className="f-btn-secondary" onClick={() => copy(feed.token, 'Token')}><Copy size={13} /></button>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs text-muted uppercase">FortiGate CLI</div>
                    <button className="f-btn-secondary" onClick={() => copy(feed.fortigate_snippet, 'CLI snippet')}>
                      <Copy size={13} /> Copy
                    </button>
                  </div>
                  <pre className="text-[11px] bg-slate-900 text-slate-100 rounded p-2 overflow-x-auto">{feed.fortigate_snippet}</pre>
                </div>
              </div>
            </div>
          );
        })}
        {feeds.length === 0 && <p className="text-muted text-table">No feeds defined.</p>}
      </div>

      <SlideOver title="Create Feed" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="Slug" hint="URL path segment, e.g. 'networks' → /feeds/networks.txt">
          <input className="f-input font-mono" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} />
        </FormField>
        <FormField label="Display name">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="Kind">
          <select className="f-input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="networks">networks — all subnets as CIDR list</option>
            <option value="tag">tag — networks/IPs carrying a tag</option>
            <option value="blocklist">blocklist — blocked IPs/CIDRs</option>
            <option value="fqdn">fqdn — domain feed from DNS records</option>
          </select>
        </FormField>
        {form.kind === 'tag' && (
          <FormField label="Tag">
            <select className="f-input" value={form.tag_id} onChange={(e) => setForm({ ...form, tag_id: e.target.value })}>
              <option value="">— select —</option>
              {tags.map((tag) => (
                <option key={tag.id} value={tag.id}>{tag.name}</option>
              ))}
            </select>
          </FormField>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={create.isPending || !form.slug || (form.kind === 'tag' && !form.tag_id)}
            onClick={() => create.mutate()}
          >
            Create
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete feed"
        message={`Delete feed ${deleting?.slug}? FortiGates consuming it will stop receiving updates.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
