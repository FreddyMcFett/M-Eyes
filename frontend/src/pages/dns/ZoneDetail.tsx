import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileCode2, SlidersHorizontal, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { DnsRecord, Zone } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import ExtAttrPanel from '../../components/ExtAttrPanel';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import SlideOver from '../../components/SlideOver';
import { useToast } from '../../components/Toast';

const RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'PTR', 'SRV'];

interface RecordForm {
  name: string;
  type: string;
  value: string;
  ttl: string;
  priority: string;
  auto_ptr: boolean;
}

const EMPTY: RecordForm = { name: '', type: 'A', value: '', ttl: '', priority: '', auto_ptr: true };

export default function ZoneDetail() {
  const { id } = useParams();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [zoneEditOpen, setZoneEditOpen] = useState(false);
  const [zoneForm, setZoneForm] = useState<Record<string, string | boolean>>({});
  const [form, setForm] = useState<RecordForm>(EMPTY);
  const [deleting, setDeleting] = useState<DnsRecord | null>(null);

  const { data: zone } = useQuery({
    queryKey: ['zone', id],
    queryFn: () => api.get<Zone>(`/api/v1/zones/${id}`),
  });
  const { data: records = [], refetch } = useQuery({
    queryKey: ['records', id],
    queryFn: () => api.get<DnsRecord[]>(`/api/v1/zones/${id}/records`),
  });
  const { data: zoneFile } = useQuery({
    queryKey: ['zone-file', id, zone?.serial],
    queryFn: () => api.get<{ content: string }>(`/api/v1/zones/${id}/file`),
    enabled: previewOpen,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['records', id] });
    queryClient.invalidateQueries({ queryKey: ['zone', id] });
  };

  const create = useMutation({
    mutationFn: () =>
      api.post(`/api/v1/zones/${id}/records`, {
        name: form.name || '@',
        type: form.type,
        value: form.value,
        ttl: form.ttl ? Number(form.ttl) : null,
        priority: form.priority ? Number(form.priority) : null,
        auto_ptr: form.type === 'A' && form.auto_ptr,
      }),
    onSuccess: () => {
      toast('success', 'Record created');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (record: DnsRecord) => api.delete(`/api/v1/records/${record.id}`),
    onSuccess: () => {
      toast('success', 'Record deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const num = (v: string | boolean | undefined) =>
    v === '' || v === undefined ? null : Number(v);

  const saveZone = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        allow_query: zoneForm.allow_query ?? '',
        allow_transfer: zoneForm.allow_transfer ?? '',
        also_notify: zoneForm.also_notify ?? '',
      };
      if (zone?.role === 'primary') {
        Object.assign(body, {
          soa_mname: zoneForm.soa_mname,
          soa_rname: zoneForm.soa_rname,
          default_ttl: num(zoneForm.default_ttl),
          refresh: num(zoneForm.refresh),
          retry: num(zoneForm.retry),
          expire: num(zoneForm.expire),
          minimum: num(zoneForm.minimum),
          allow_update: zoneForm.allow_update ?? '',
          dnssec_enabled: Boolean(zoneForm.dnssec_enabled),
        });
      }
      if (zone?.role === 'forward') body.forward_first = Boolean(zoneForm.forward_first);
      return api.patch(`/api/v1/zones/${id}`, body);
    },
    onSuccess: () => {
      toast('success', 'Zone updated — applying to the DNS service');
      setZoneEditOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const openZoneEditor = () => {
    if (!zone) return;
    setZoneForm({
      soa_mname: zone.soa_mname,
      soa_rname: zone.soa_rname,
      default_ttl: String(zone.default_ttl),
      refresh: String(zone.refresh),
      retry: String(zone.retry),
      expire: String(zone.expire),
      minimum: String(zone.minimum),
      dnssec_enabled: zone.dnssec_enabled,
      allow_query: zone.allow_query ?? '',
      allow_transfer: zone.allow_transfer ?? '',
      allow_update: zone.allow_update ?? '',
      also_notify: zone.also_notify ?? '',
      forward_first: zone.forward_first ?? false,
    });
    setZoneEditOpen(true);
  };
  const zf = (key: string) => (zoneForm[key] as string) ?? '';

  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <Link to="/dns" className="text-info hover:underline flex items-center gap-1 text-table">
          <ArrowLeft size={14} /> Zones
        </Link>
        <h1 className="text-lg font-semibold font-mono">{zone?.name}</h1>
        <span className="text-muted text-table">serial {zone?.serial}</span>
        <span className="px-2 py-0.5 rounded bg-slate-200 text-xs font-mono">
          view: {zone?.view_name ?? 'default'}
        </span>
        {zone?.dnssec_enabled && (
          <span className="px-2 py-0.5 rounded bg-accent/20 text-accent text-xs font-semibold">
            DNSSEC
          </span>
        )}
      </div>

      {zone && (
        <div className="f-card p-4 mb-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-table">
          <div>
            <div className="text-xs text-muted uppercase">Primary NS (MNAME)</div>
            <div className="font-mono">{zone.soa_mname}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Contact (RNAME)</div>
            <div className="font-mono">{zone.soa_rname}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Refresh / Retry</div>
            <div>{zone.refresh} / {zone.retry}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Expire / Minimum</div>
            <div>{zone.expire} / {zone.minimum}</div>
          </div>
        </div>
      )}

      <DataTable
        columns={[
          { header: 'Name', searchText: (r: DnsRecord) => r.name, render: (r) => <span className="font-mono">{r.name}</span> },
          { header: 'Type', searchText: (r: DnsRecord) => r.type, render: (r) => <span className="font-semibold">{r.type}</span> },
          {
            header: 'Value',
            searchText: (r: DnsRecord) => r.value,
            render: (r) => (
              <span className="font-mono">
                {r.priority !== null && <span className="text-muted mr-1">{r.priority}</span>}
                {r.value}
              </span>
            ),
          },
          { header: 'TTL', render: (r) => <span>{r.ttl ?? 'default'}</span> },
          {
            header: 'Actions',
            render: (r) => (
              <button onClick={() => setDeleting(r)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={records}
        rowKey={(r) => r.id}
        onCreate={() => {
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Add Record"
        onRefresh={() => refetch()}
        toolbar={
          <>
            <button className="f-btn-secondary" onClick={openZoneEditor}>
              <SlidersHorizontal size={14} /> Edit zone
            </button>
            <button className="f-btn-secondary" onClick={() => setPreviewOpen(true)}>
              <FileCode2 size={14} /> Preview zone file
            </button>
          </>
        }
      />

      {id && <ExtAttrPanel objectType="zone" objectId={id} />}

      <SlideOver title={`Edit zone — ${zone?.name ?? ''}`} open={zoneEditOpen} onClose={() => setZoneEditOpen(false)}>
        {zone?.role === 'primary' && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Primary NS (MNAME)">
                <input className="f-input font-mono" value={zf('soa_mname')} onChange={(e) => setZoneForm({ ...zoneForm, soa_mname: e.target.value })} />
              </FormField>
              <FormField label="Contact (RNAME)">
                <input className="f-input font-mono" value={zf('soa_rname')} onChange={(e) => setZoneForm({ ...zoneForm, soa_rname: e.target.value })} />
              </FormField>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <FormField label="Default TTL">
                <input className="f-input" type="number" value={zf('default_ttl')} onChange={(e) => setZoneForm({ ...zoneForm, default_ttl: e.target.value })} />
              </FormField>
              <FormField label="Refresh">
                <input className="f-input" type="number" value={zf('refresh')} onChange={(e) => setZoneForm({ ...zoneForm, refresh: e.target.value })} />
              </FormField>
              <FormField label="Retry">
                <input className="f-input" type="number" value={zf('retry')} onChange={(e) => setZoneForm({ ...zoneForm, retry: e.target.value })} />
              </FormField>
              <FormField label="Expire">
                <input className="f-input" type="number" value={zf('expire')} onChange={(e) => setZoneForm({ ...zoneForm, expire: e.target.value })} />
              </FormField>
              <FormField label="Minimum (negative TTL)">
                <input className="f-input" type="number" value={zf('minimum')} onChange={(e) => setZoneForm({ ...zoneForm, minimum: e.target.value })} />
              </FormField>
            </div>
            <FormField label="DNSSEC">
              <label className="flex items-center gap-2 text-table">
                <input type="checkbox" checked={Boolean(zoneForm.dnssec_enabled)} onChange={(e) => setZoneForm({ ...zoneForm, dnssec_enabled: e.target.checked })} />
                Enable inline signing
              </label>
            </FormField>
          </>
        )}
        {zone?.role === 'forward' && (
          <FormField label="Forwarding mode" hint="Forward-first falls back to normal resolution if forwarders do not answer">
            <label className="flex items-center gap-2 text-table">
              <input type="checkbox" checked={Boolean(zoneForm.forward_first)} onChange={(e) => setZoneForm({ ...zoneForm, forward_first: e.target.checked })} />
              Forward first (otherwise forward only)
            </label>
          </FormField>
        )}
        {zone?.role !== 'forward' && (
          <>
            <FormField label="Allow query" hint="Who may query this zone (e.g. any, 10.0.0.0/8, localnets). Empty = server default.">
              <input className="f-input font-mono" placeholder="any" value={zf('allow_query')} onChange={(e) => setZoneForm({ ...zoneForm, allow_query: e.target.value })} />
            </FormField>
            <FormField label="Allow zone transfer" hint="Secondaries permitted to transfer the zone. Empty = none.">
              <input className="f-input font-mono" placeholder="none" value={zf('allow_transfer')} onChange={(e) => setZoneForm({ ...zoneForm, allow_transfer: e.target.value })} />
            </FormField>
            <FormField label="Also notify" hint="Extra servers to notify on change (comma-separated IPs).">
              <input className="f-input font-mono" placeholder="192.0.2.53" value={zf('also_notify')} onChange={(e) => setZoneForm({ ...zoneForm, also_notify: e.target.value })} />
            </FormField>
            {zone?.role === 'primary' && (
              <FormField label="Allow dynamic update" hint="ACL permitted to send dynamic DNS updates. Empty = none.">
                <input className="f-input font-mono" placeholder="none" value={zf('allow_update')} onChange={(e) => setZoneForm({ ...zoneForm, allow_update: e.target.value })} />
              </FormField>
            )}
          </>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setZoneEditOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={saveZone.isPending} onClick={() => saveZone.mutate()}>Save</button>
        </div>
      </SlideOver>

      <SlideOver title="Add Record" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="Name" hint="Relative name; use @ for the zone apex">
          <input className="f-input font-mono" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="@" />
        </FormField>
        <FormField label="Type">
          <select className="f-input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            {RECORD_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Value">
          <input className="f-input font-mono" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
        </FormField>
        {(form.type === 'MX' || form.type === 'SRV') && (
          <FormField label="Priority">
            <input className="f-input" type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} placeholder="10" />
          </FormField>
        )}
        <FormField label="TTL" hint="Leave empty for zone default">
          <input className="f-input" type="number" value={form.ttl} onChange={(e) => setForm({ ...form, ttl: e.target.value })} />
        </FormField>
        {form.type === 'A' && zone?.kind === 'forward' && (
          <FormField label="Reverse DNS">
            <label className="flex items-center gap-2 text-table">
              <input type="checkbox" checked={form.auto_ptr} onChange={(e) => setForm({ ...form, auto_ptr: e.target.checked })} />
              Automatically create/update the PTR record
            </label>
          </FormField>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={create.isPending || !form.value} onClick={() => create.mutate()}>
            Add
          </button>
        </div>
      </SlideOver>

      <Modal title={`Zone file — ${zone?.name}`} open={previewOpen} onClose={() => setPreviewOpen(false)} wide>
        <pre className="bg-slate-900 text-slate-100 rounded p-3 text-xs overflow-x-auto whitespace-pre">
          {zoneFile?.content ?? 'Loading…'}
        </pre>
      </Modal>

      <ConfirmDialog
        title="Delete record"
        message={`Delete ${deleting?.type} record "${deleting?.name}"?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
