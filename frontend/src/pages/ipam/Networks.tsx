import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FolderPlus, Folder, Pencil, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { Network, Tag } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import TagChip from '../../components/TagChip';
import { useToast } from '../../components/Toast';

interface NetworkForm {
  cidr: string;
  name: string;
  description: string;
  is_container: boolean;
  vlan: string;
  site: string;
  tag_ids: number[];
}

const EMPTY: NetworkForm = { cidr: '', name: '', description: '', is_container: false, vlan: '', site: '', tag_ids: [] };

export default function Networks() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Network | null>(null);
  const [form, setForm] = useState<NetworkForm>(EMPTY);
  const [deleting, setDeleting] = useState<Network | null>(null);
  const [allocating, setAllocating] = useState<Network | null>(null);
  const [allocForm, setAllocForm] = useState({ prefixlen: '24', name: '' });

  const { data: networks = [], refetch } = useQuery({
    queryKey: ['networks'],
    queryFn: () => api.get<Network[]>('/api/v1/networks'),
  });
  const { data: tags = [] } = useQuery({
    queryKey: ['tags'],
    queryFn: () => api.get<Tag[]>('/api/v1/tags'),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['networks'] });

  const save = useMutation({
    mutationFn: () => {
      const payload = {
        cidr: form.cidr,
        name: form.name,
        description: form.description,
        is_container: form.is_container,
        vlan: form.vlan ? Number(form.vlan) : null,
        site: form.site,
        tag_ids: form.tag_ids,
      };
      return editing
        ? api.patch(`/api/v1/networks/${editing.id}`, payload)
        : api.post('/api/v1/networks', payload);
    },
    onSuccess: () => {
      toast('success', editing ? 'Network updated' : 'Network created');
      setEditorOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (network: Network) => api.delete(`/api/v1/networks/${network.id}`),
    onSuccess: () => {
      toast('success', 'Network deleted');
      setDeleting(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const allocate = useMutation({
    mutationFn: () =>
      api.post<Network>(`/api/v1/networks/${allocating!.id}/allocate-subnet`, {
        prefixlen: Number(allocForm.prefixlen),
        name: allocForm.name,
      }),
    onSuccess: (network) => {
      toast('success', `Allocated ${network.cidr}`);
      setAllocating(null);
      invalidate();
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY);
    setEditorOpen(true);
  };
  const openEdit = (network: Network) => {
    setEditing(network);
    setForm({
      cidr: network.cidr,
      name: network.name,
      description: network.description,
      is_container: network.is_container,
      vlan: network.vlan?.toString() ?? '',
      site: network.site,
      tag_ids: network.tags.map((t) => t.id),
    });
    setEditorOpen(true);
  };

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">IPAM — Networks</h1>
      <DataTable
        columns={[
          {
            header: 'CIDR',
            searchText: (n: Network) => n.cidr,
            render: (n) => (
              <span className="flex items-center gap-1.5 font-mono">
                {n.is_container && <Folder size={13} className="text-warning" />}
                {n.parent_id && <span className="text-muted">└</span>}
                <Link to={`/ipam/${n.id}`} className="text-info hover:underline">
                  {n.cidr}
                </Link>
              </span>
            ),
          },
          { header: 'Name', searchText: (n: Network) => n.name, render: (n) => <span>{n.name}</span> },
          { header: 'VLAN', searchText: (n: Network) => String(n.vlan ?? ''), render: (n) => <span>{n.vlan ?? '—'}</span> },
          { header: 'Site', searchText: (n: Network) => n.site, render: (n) => <span>{n.site || '—'}</span> },
          {
            header: 'Tags',
            searchText: (n: Network) => n.tags.map((t) => t.name).join(' '),
            render: (n) => (
              <span>
                {n.tags.map((tag) => (
                  <TagChip key={tag.id} tag={tag} />
                ))}
              </span>
            ),
          },
          {
            header: 'Utilization',
            render: (n) =>
              n.is_container || !n.utilization ? (
                <span className="text-muted">—</span>
              ) : (
                <div className="flex items-center gap-2 min-w-[120px]">
                  <div className="flex-1 h-2 bg-slate-200 rounded overflow-hidden">
                    <div
                      className={`h-full ${n.utilization.percent > 90 ? 'bg-danger' : n.utilization.percent > 70 ? 'bg-warning' : 'bg-accent'}`}
                      style={{ width: `${Math.min(n.utilization.percent, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted w-12">{n.utilization.percent}%</span>
                </div>
              ),
          },
          {
            header: 'Actions',
            render: (n) => (
              <span className="flex gap-2">
                {n.is_container && (
                  <button
                    onClick={() => {
                      setAllocForm({ prefixlen: '24', name: '' });
                      setAllocating(n);
                    }}
                    className="text-accent hover:opacity-70"
                    title="Allocate next free subnet"
                  >
                    <FolderPlus size={14} />
                  </button>
                )}
                <button onClick={() => openEdit(n)} className="text-info hover:opacity-70" title="Edit">
                  <Pencil size={14} />
                </button>
                <button onClick={() => setDeleting(n)} className="text-danger hover:opacity-70" title="Delete">
                  <Trash2 size={14} />
                </button>
              </span>
            ),
          },
        ]}
        rows={networks}
        rowKey={(n) => n.id}
        onCreate={openCreate}
        createLabel="Create Network"
        onRefresh={() => refetch()}
      />

      <SlideOver title={editing ? `Edit ${editing.cidr}` : 'Create Network'} open={editorOpen} onClose={() => setEditorOpen(false)}>
        <FormField label="CIDR" hint="e.g. 10.10.1.0/24">
          <input className="f-input font-mono" value={form.cidr} onChange={(e) => setForm({ ...form, cidr: e.target.value })} />
        </FormField>
        <FormField label="Name">
          <input className="f-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </FormField>
        <FormField label="Description">
          <input className="f-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="VLAN">
            <input className="f-input" type="number" value={form.vlan} onChange={(e) => setForm({ ...form, vlan: e.target.value })} />
          </FormField>
          <FormField label="Site">
            <input className="f-input" value={form.site} onChange={(e) => setForm({ ...form, site: e.target.value })} />
          </FormField>
        </div>
        <FormField label="Container" hint="Containers group subnets and hold no IPs themselves">
          <label className="flex items-center gap-2 text-table">
            <input
              type="checkbox"
              checked={form.is_container}
              onChange={(e) => setForm({ ...form, is_container: e.target.checked })}
            />
            This network is a container
          </label>
        </FormField>
        <FormField label="Tags">
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <label key={tag.id} className="flex items-center gap-1 text-table border border-line rounded px-2 py-1">
                <input
                  type="checkbox"
                  checked={form.tag_ids.includes(tag.id)}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      tag_ids: e.target.checked
                        ? [...form.tag_ids, tag.id]
                        : form.tag_ids.filter((id) => id !== tag.id),
                    })
                  }
                />
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: tag.color }} />
                {tag.name}
              </label>
            ))}
            {tags.length === 0 && <span className="text-muted text-xs">No tags defined yet</span>}
          </div>
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>
            Cancel
          </button>
          <button className="f-btn-primary" disabled={save.isPending || !form.cidr} onClick={() => save.mutate()}>
            {editing ? 'Save' : 'Create'}
          </button>
        </div>
      </SlideOver>

      <SlideOver
        title={`Allocate next subnet in ${allocating?.cidr ?? ''}`}
        open={allocating !== null}
        onClose={() => setAllocating(null)}
      >
        <p className="text-table text-muted mb-3">
          Finds the first free CIDR of the requested size inside the container and creates it
          (Infoblox-style “next available network”).
        </p>
        <FormField label="Prefix length" hint="e.g. 24 for a /24">
          <input
            className="f-input"
            type="number"
            min={1}
            max={30}
            value={allocForm.prefixlen}
            onChange={(e) => setAllocForm({ ...allocForm, prefixlen: e.target.value })}
          />
        </FormField>
        <FormField label="Name">
          <input className="f-input" value={allocForm.name} onChange={(e) => setAllocForm({ ...allocForm, name: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setAllocating(null)}>
            Cancel
          </button>
          <button
            className="f-btn-primary"
            disabled={allocate.isPending || !allocForm.prefixlen}
            onClick={() => allocate.mutate()}
          >
            Allocate
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete network"
        message={`Delete ${deleting?.cidr}? All IP allocations inside it will be removed.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
