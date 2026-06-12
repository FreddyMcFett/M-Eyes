import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { Host, Network, Zone } from '../api/types';
import DataTable from '../components/DataTable';
import ConfirmDialog from '../components/ConfirmDialog';
import FormField from '../components/FormField';
import SlideOver from '../components/SlideOver';
import { useToast } from '../components/Toast';

interface HostForm {
  hostname: string;
  zone: string;
  network_id: string;
  ip: string;
  mac: string;
  create_reservation: boolean;
}

const EMPTY: HostForm = { hostname: '', zone: '', network_id: '', ip: '', mac: '', create_reservation: false };

export default function Hosts() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState<HostForm>(EMPTY);
  const [deleting, setDeleting] = useState<Host | null>(null);

  const { data: hosts = [], refetch } = useQuery({
    queryKey: ['hosts'],
    queryFn: () => api.get<Host[]>('/api/v1/hosts'),
  });
  const { data: networks = [] } = useQuery({
    queryKey: ['networks'],
    queryFn: () => api.get<Network[]>('/api/v1/networks'),
  });
  const { data: zones = [] } = useQuery({
    queryKey: ['zones'],
    queryFn: () => api.get<Zone[]>('/api/v1/zones'),
  });

  const forwardZones = zones.filter((z) => z.kind === 'forward');

  const create = useMutation({
    mutationFn: () =>
      api.post('/api/v1/hosts', {
        name: `${form.hostname}.${form.zone}`,
        network_id: Number(form.network_id),
        ip: form.ip || null,
        mac: form.mac || null,
        create_reservation: form.create_reservation,
      }),
    onSuccess: () => {
      toast('success', 'Host created (IP + A + PTR records)');
      setEditorOpen(false);
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (host: Host) => api.delete(`/api/v1/hosts/${host.id}`),
    onSuccess: () => {
      toast('success', 'Host and all linked objects deleted');
      setDeleting(null);
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">Hosts</h1>
      <p className="text-table text-muted mb-3">
        A host is a composite object: creating one allocates an IP in IPAM, creates the A and PTR
        records, and optionally a DHCP reservation — all in one step.
      </p>
      <DataTable
        columns={[
          { header: 'FQDN', searchText: (h: Host) => h.name, render: (h) => <span className="font-mono">{h.name}</span> },
          { header: 'IP', searchText: (h: Host) => h.ip ?? '', render: (h) => <span className="font-mono">{h.ip ?? '—'}</span> },
          { header: 'Zone', render: (h) => <span>{h.zone_name ?? '—'}</span> },
          {
            header: 'Linked objects',
            render: (h) => (
              <span className="text-xs text-muted">
                {[
                  h.ip_address_id && 'IP',
                  h.a_record_id && 'A',
                  h.ptr_record_id && 'PTR',
                  h.reservation_id && 'DHCP',
                ]
                  .filter(Boolean)
                  .join(' + ')}
              </span>
            ),
          },
          {
            header: 'Actions',
            render: (h) => (
              <button onClick={() => setDeleting(h)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={hosts}
        rowKey={(h) => h.id}
        onCreate={() => {
          setForm(EMPTY);
          setEditorOpen(true);
        }}
        createLabel="Smart Create Host"
        onRefresh={() => refetch()}
      />

      <SlideOver title="Smart Create Host" open={editorOpen} onClose={() => setEditorOpen(false)}>
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Hostname">
            <input className="f-input font-mono" value={form.hostname} onChange={(e) => setForm({ ...form, hostname: e.target.value })} placeholder="srv1" />
          </FormField>
          <FormField label="Zone">
            <select className="f-input" value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })}>
              <option value="">— zone —</option>
              {forwardZones.map((z) => (
                <option key={z.id} value={z.name}>{z.name}</option>
              ))}
            </select>
          </FormField>
        </div>
        <FormField label="Network">
          <select className="f-input" value={form.network_id} onChange={(e) => setForm({ ...form, network_id: e.target.value })}>
            <option value="">— network —</option>
            {networks.filter((n) => !n.is_container).map((n) => (
              <option key={n.id} value={n.id}>{n.cidr} {n.name && `(${n.name})`}</option>
            ))}
          </select>
        </FormField>
        <FormField label="IP address" hint="Leave empty to auto-allocate the next free IP">
          <input className="f-input font-mono" value={form.ip} onChange={(e) => setForm({ ...form, ip: e.target.value })} placeholder="auto" />
        </FormField>
        <FormField label="MAC address" hint="Required for a DHCP reservation">
          <input className="f-input font-mono" value={form.mac} onChange={(e) => setForm({ ...form, mac: e.target.value })} />
        </FormField>
        <FormField label="DHCP">
          <label className="flex items-center gap-2 text-table">
            <input
              type="checkbox"
              checked={form.create_reservation}
              onChange={(e) => setForm({ ...form, create_reservation: e.target.checked })}
            />
            Also create a DHCP reservation
          </label>
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditorOpen(false)}>Cancel</button>
          <button
            className="f-btn-primary"
            disabled={create.isPending || !form.hostname || !form.zone || !form.network_id}
            onClick={() => create.mutate()}
          >
            Create
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete host"
        message={`Delete ${deleting?.name}? The IP allocation, A/PTR records and DHCP reservation will also be removed.`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
