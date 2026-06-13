import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link2, Plus, RefreshCcw, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { Asset, AssetInterface, AssetMeta } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

interface AssetForm {
  id: number | null;
  name: string;
  asset_type: string;
  status: string;
  criticality: string;
  owner: string;
  location: string;
  department: string;
  vendor: string;
  model: string;
  serial_number: string;
  operating_system: string;
  description: string;
  interfaces: AssetInterface[];
}

const EMPTY: AssetForm = {
  id: null, name: '', asset_type: 'server', status: 'in_service', criticality: 'medium',
  owner: '', location: '', department: '', vendor: '', model: '', serial_number: '',
  operating_system: '', description: '', interfaces: [],
};

const blankIface = (): AssetInterface => ({ name: '', mac: '', ip: '', hostname: '', ip_id: null });

export default function Assets() {
  const toast = useToast();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<AssetForm>(EMPTY);
  const [deleting, setDeleting] = useState<Asset | null>(null);

  const { data: assets = [], refetch } = useQuery({
    queryKey: ['assets'],
    queryFn: () => api.get<Asset[]>('/api/v1/assets'),
  });
  const { data: meta } = useQuery({
    queryKey: ['asset-meta'],
    queryFn: () => api.get<AssetMeta>('/api/v1/assets/meta'),
  });

  const payload = (f: AssetForm) => ({
    name: f.name, asset_type: f.asset_type, status: f.status, criticality: f.criticality,
    owner: f.owner, location: f.location, department: f.department, vendor: f.vendor,
    model: f.model, serial_number: f.serial_number, operating_system: f.operating_system,
    description: f.description,
    interfaces: f.interfaces.filter((i) => i.ip || i.mac || i.hostname),
  });

  const save = useMutation({
    mutationFn: (f: AssetForm) =>
      f.id ? api.patch(`/api/v1/assets/${f.id}`, payload(f)) : api.post('/api/v1/assets', payload(f)),
    onSuccess: () => {
      toast('success', form.id ? 'Asset updated' : 'Asset created');
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (a: Asset) => api.delete(`/api/v1/assets/${a.id}`),
    onSuccess: () => {
      toast('success', 'Asset deleted');
      setDeleting(null);
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const sync = useMutation({
    mutationFn: () => api.post<{ detail: string }>('/api/v1/assets/sync'),
    onSuccess: (r) => {
      toast('success', r.detail);
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const edit = (a: Asset) => {
    setForm({
      id: a.id, name: a.name, asset_type: a.asset_type, status: a.status, criticality: a.criticality,
      owner: a.owner, location: a.location, department: a.department, vendor: a.vendor, model: a.model,
      serial_number: a.serial_number, operating_system: a.operating_system, description: a.description,
      interfaces: a.interfaces.map((i) => ({ ...i })),
    });
    setOpen(true);
  };

  return (
    <>
      <h1 className="text-lg font-semibold mb-1">Asset Management</h1>
      <p className="text-table text-muted mb-3">
        An enterprise CMDB cross-referenced to your DDI data. Asset interfaces link to IPAM
        addresses by MAC/IP, so you can pivot from any address or lease to the owning device,
        its owner, location and lifecycle state. <strong>Reconcile from DDI</strong> mints and
        links assets from managed IPAM records automatically.
      </p>
      <DataTable
        columns={[
          { header: 'Name', searchText: (a: Asset) => a.name, render: (a) => <span className="font-medium">{a.name}</span> },
          { header: 'Type', render: (a) => <span className="text-xs">{a.asset_type}</span> },
          { header: 'Status', render: (a) => <StatusBadge value={a.status === 'in_service' ? 'used' : a.status} /> },
          { header: 'Criticality', render: (a) => <span className="text-xs">{a.criticality}</span> },
          { header: 'Owner', searchText: (a: Asset) => a.owner, render: (a) => <span className="text-xs">{a.owner || '—'}</span> },
          {
            header: 'Addresses',
            searchText: (a: Asset) => a.interfaces.map((i) => `${i.ip} ${i.mac}`).join(' '),
            render: (a) => (
              <span className="font-mono text-xs">
                {a.interfaces.length === 0 ? '—' : a.interfaces.map((i, idx) => (
                  <span key={idx} className="inline-flex items-center gap-1 mr-2">
                    {i.ip_id && <Link2 size={11} className="text-accent" />}
                    {i.ip || i.mac}
                  </span>
                ))}
              </span>
            ),
          },
          { header: 'Source', render: (a) => <span className="text-xs text-muted">{a.source}</span> },
          {
            header: 'Actions',
            render: (a) => (
              <div className="flex gap-2">
                <button onClick={() => edit(a)} className="text-accent hover:opacity-70 text-xs">Edit</button>
                <button onClick={() => setDeleting(a)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </div>
            ),
          },
        ]}
        rows={assets}
        rowKey={(a) => a.id}
        onCreate={() => { setForm(EMPTY); setOpen(true); }}
        createLabel="New Asset"
        onRefresh={() => refetch()}
        toolbar={
          <button className="f-btn-secondary" onClick={() => sync.mutate()} disabled={sync.isPending}>
            <RefreshCcw size={14} /> Reconcile from DDI
          </button>
        }
      />

      <SlideOver title={form.id ? 'Edit asset' : 'New asset'} open={open} onClose={() => setOpen(false)}>
        <FormField label="Name">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Type">
            <select className="f-input" value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value })}>
              {meta?.types.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </FormField>
          <FormField label="Status">
            <select className="f-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {meta?.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </FormField>
          <FormField label="Criticality">
            <select className="f-input" value={form.criticality} onChange={(e) => setForm({ ...form, criticality: e.target.value })}>
              {meta?.criticality.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </FormField>
          <FormField label="Owner">
            <input className="f-input" value={form.owner} onChange={(e) => setForm({ ...form, owner: e.target.value })} />
          </FormField>
          <FormField label="Location">
            <input className="f-input" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
          </FormField>
          <FormField label="Department">
            <input className="f-input" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
          </FormField>
          <FormField label="Vendor">
            <input className="f-input" value={form.vendor} onChange={(e) => setForm({ ...form, vendor: e.target.value })} />
          </FormField>
          <FormField label="Model">
            <input className="f-input" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
          </FormField>
          <FormField label="Serial">
            <input className="f-input" value={form.serial_number} onChange={(e) => setForm({ ...form, serial_number: e.target.value })} />
          </FormField>
          <FormField label="Operating system">
            <input className="f-input" value={form.operating_system} onChange={(e) => setForm({ ...form, operating_system: e.target.value })} />
          </FormField>
        </div>
        <FormField label="Description">
          <textarea className="f-input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </FormField>

        <div className="flex items-center justify-between mt-2 mb-1">
          <span className="f-label">Interfaces</span>
          <button className="text-accent text-xs flex items-center gap-1"
                  onClick={() => setForm({ ...form, interfaces: [...form.interfaces, blankIface()] })}>
            <Plus size={12} /> Add interface
          </button>
        </div>
        {form.interfaces.map((iface, idx) => (
          <div key={idx} className="grid grid-cols-3 gap-1 mb-2 items-center">
            <input className="f-input font-mono text-xs" placeholder="IP" value={iface.ip}
                   onChange={(e) => {
                     const next = [...form.interfaces];
                     next[idx] = { ...iface, ip: e.target.value };
                     setForm({ ...form, interfaces: next });
                   }} />
            <input className="f-input font-mono text-xs" placeholder="MAC" value={iface.mac}
                   onChange={(e) => {
                     const next = [...form.interfaces];
                     next[idx] = { ...iface, mac: e.target.value };
                     setForm({ ...form, interfaces: next });
                   }} />
            <div className="flex gap-1">
              <input className="f-input text-xs" placeholder="hostname" value={iface.hostname}
                     onChange={(e) => {
                       const next = [...form.interfaces];
                       next[idx] = { ...iface, hostname: e.target.value };
                       setForm({ ...form, interfaces: next });
                     }} />
              <button className="text-danger" onClick={() =>
                setForm({ ...form, interfaces: form.interfaces.filter((_, i) => i !== idx) })}>
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}

        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={save.isPending || !form.name} onClick={() => save.mutate(form)}>
            {form.id ? 'Save' : 'Create'}
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete asset"
        message={`Delete ${deleting?.name}? This removes the asset and its interface links (DDI records are untouched).`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
