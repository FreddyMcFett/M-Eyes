import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, FileCode2, Plus, SlidersHorizontal, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { DhcpSubnet } from '../../api/types';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import Modal from '../../components/Modal';
import SlideOver from '../../components/SlideOver';
import { useToast } from '../../components/Toast';

type Editor = 'range' | 'reservation' | 'option' | 'settings' | null;

const OPTION_NAMES = ['routers', 'domain-name-servers', 'domain-name', 'ntp-servers', 'time-servers'];

const EMPTY_SETTINGS = {
  valid_lifetime: '', max_valid_lifetime: '', renew_timer: '', rebind_timer: '',
  next_server: '', boot_file_name: '', client_class: '',
};

export default function SubnetDetail() {
  const { id } = useParams();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [editor, setEditor] = useState<Editor>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [rangeForm, setRangeForm] = useState({ start_ip: '', end_ip: '' });
  const [reservationForm, setReservationForm] = useState({ mac: '', ip: '', hostname: '' });
  const [optionForm, setOptionForm] = useState({ name: 'routers', value: '' });
  const [settingsForm, setSettingsForm] = useState<Record<string, string>>(EMPTY_SETTINGS);
  const [confirm, setConfirm] = useState<{ kind: string; id: number; label: string } | null>(null);

  const { data: subnet } = useQuery({
    queryKey: ['dhcp-subnet', id],
    queryFn: () => api.get<DhcpSubnet>(`/api/v1/dhcp/subnets/${id}`),
  });
  const { data: preview } = useQuery({
    queryKey: ['kea-preview'],
    queryFn: () => api.get<{ kea_dhcp4_conf: string }>('/api/v1/deploy/kea/preview'),
    enabled: previewOpen,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['dhcp-subnet', id] });

  const onError = (err: Error) => toast('error', err.message);
  const onDone = (message: string) => {
    toast('success', message);
    setEditor(null);
    setConfirm(null);
    invalidate();
  };

  const addRange = useMutation({
    mutationFn: () => api.post(`/api/v1/dhcp/subnets/${id}/ranges`, rangeForm),
    onSuccess: () => onDone('Range added'),
    onError,
  });
  const addReservation = useMutation({
    mutationFn: () => api.post(`/api/v1/dhcp/subnets/${id}/reservations`, reservationForm),
    onSuccess: () => onDone('Reservation added'),
    onError,
  });
  const addOption = useMutation({
    mutationFn: () => api.post(`/api/v1/dhcp/subnets/${id}/options`, optionForm),
    onSuccess: () => onDone('Option set'),
    onError,
  });
  const saveSettings = useMutation({
    mutationFn: () => {
      const numeric = ['valid_lifetime', 'max_valid_lifetime', 'renew_timer', 'rebind_timer'];
      const body: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(settingsForm)) {
        const trimmed = value.trim();
        body[key] = trimmed === '' ? null : numeric.includes(key) ? Number(trimmed) : trimmed;
      }
      return api.patch(`/api/v1/dhcp/subnets/${id}`, body);
    },
    onSuccess: () => onDone('Settings saved — deploy DHCP to apply'),
    onError,
  });

  const openSettings = () => {
    if (!subnet) return;
    setSettingsForm({
      valid_lifetime: subnet.valid_lifetime?.toString() ?? '',
      max_valid_lifetime: subnet.max_valid_lifetime?.toString() ?? '',
      renew_timer: subnet.renew_timer?.toString() ?? '',
      rebind_timer: subnet.rebind_timer?.toString() ?? '',
      next_server: subnet.next_server ?? '',
      boot_file_name: subnet.boot_file_name ?? '',
      client_class: subnet.client_class ?? '',
    });
    setEditor('settings');
  };
  const sf = (key: string, value: string) => setSettingsForm((f) => ({ ...f, [key]: value }));
  const removeItem = useMutation({
    mutationFn: ({ kind, id: itemId }: { kind: string; id: number }) =>
      api.delete(`/api/v1/dhcp/${kind}/${itemId}`),
    onSuccess: () => onDone('Removed'),
    onError,
  });

  const section = (title: string, action: () => void, children: React.ReactNode) => (
    <div className="f-card mb-4">
      <div className="flex items-center justify-between px-3 py-2 border-b border-line">
        <h3 className="font-semibold text-table">{title}</h3>
        <button className="f-btn-primary" onClick={action}>
          <Plus size={13} /> Add
        </button>
      </div>
      {children}
    </div>
  );

  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <Link to="/dhcp" className="text-info hover:underline flex items-center gap-1 text-table">
          <ArrowLeft size={14} /> DHCP
        </Link>
        <h1 className="text-lg font-semibold font-mono">{subnet?.cidr}</h1>
        <button className="f-btn-secondary ml-auto" onClick={() => setPreviewOpen(true)}>
          <FileCode2 size={14} /> Preview DHCP config
        </button>
      </div>

      <div className="f-card mb-4">
        <div className="flex items-center justify-between px-3 py-2 border-b border-line">
          <h3 className="font-semibold text-table">Advanced Settings</h3>
          <button className="f-btn-secondary" onClick={openSettings}>
            <SlidersHorizontal size={13} /> Edit
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 text-table">
          <div>
            <div className="text-xs text-muted uppercase">Lease time</div>
            <div className="font-mono">{subnet?.valid_lifetime ?? 'default'}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Renew / Rebind</div>
            <div className="font-mono">{subnet?.renew_timer ?? '—'} / {subnet?.rebind_timer ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Boot server / file</div>
            <div className="font-mono break-all">{subnet?.next_server || '—'} / {subnet?.boot_file_name || '—'}</div>
          </div>
          <div>
            <div className="text-xs text-muted uppercase">Client class</div>
            <div className="font-mono">{subnet?.client_class || '—'}</div>
          </div>
        </div>
      </div>

      {section('Address Ranges', () => setEditor('range'), (
        <table className="f-table">
          <thead>
            <tr><th>Start</th><th>End</th><th className="w-20">Actions</th></tr>
          </thead>
          <tbody>
            {subnet?.ranges.map((r) => (
              <tr key={r.id}>
                <td className="font-mono">{r.start_ip}</td>
                <td className="font-mono">{r.end_ip}</td>
                <td>
                  <button
                    className="text-danger hover:opacity-70"
                    onClick={() => setConfirm({ kind: 'ranges', id: r.id, label: `${r.start_ip}-${r.end_ip}` })}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {subnet?.ranges.length === 0 && (
              <tr><td colSpan={3} className="text-center text-muted py-4">No ranges</td></tr>
            )}
          </tbody>
        </table>
      ))}

      {section('Reservations', () => setEditor('reservation'), (
        <table className="f-table">
          <thead>
            <tr><th>MAC</th><th>IP</th><th>Hostname</th><th className="w-20">Actions</th></tr>
          </thead>
          <tbody>
            {subnet?.reservations.map((r) => (
              <tr key={r.id}>
                <td className="font-mono">{r.mac}</td>
                <td className="font-mono">{r.ip}</td>
                <td>{r.hostname || '—'}</td>
                <td>
                  <button
                    className="text-danger hover:opacity-70"
                    onClick={() => setConfirm({ kind: 'reservations', id: r.id, label: r.mac })}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {subnet?.reservations.length === 0 && (
              <tr><td colSpan={4} className="text-center text-muted py-4">No reservations</td></tr>
            )}
          </tbody>
        </table>
      ))}

      {section('Options', () => setEditor('option'), (
        <table className="f-table">
          <thead>
            <tr><th>Option</th><th>Value</th><th className="w-20">Actions</th></tr>
          </thead>
          <tbody>
            {subnet?.options.map((o) => (
              <tr key={o.id}>
                <td className="font-mono">{o.name}</td>
                <td className="font-mono">{o.value}</td>
                <td>
                  <button
                    className="text-danger hover:opacity-70"
                    onClick={() => setConfirm({ kind: 'options', id: o.id, label: o.name })}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {subnet?.options.length === 0 && (
              <tr><td colSpan={3} className="text-center text-muted py-4">No options</td></tr>
            )}
          </tbody>
        </table>
      ))}

      <SlideOver title="Add Range" open={editor === 'range'} onClose={() => setEditor(null)}>
        <FormField label="Start IP">
          <input className="f-input font-mono" value={rangeForm.start_ip} onChange={(e) => setRangeForm({ ...rangeForm, start_ip: e.target.value })} />
        </FormField>
        <FormField label="End IP">
          <input className="f-input font-mono" value={rangeForm.end_ip} onChange={(e) => setRangeForm({ ...rangeForm, end_ip: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditor(null)}>Cancel</button>
          <button className="f-btn-primary" onClick={() => addRange.mutate()}>Add</button>
        </div>
      </SlideOver>

      <SlideOver title="Add Reservation" open={editor === 'reservation'} onClose={() => setEditor(null)}>
        <FormField label="MAC address" hint="aa:bb:cc:dd:ee:ff">
          <input className="f-input font-mono" value={reservationForm.mac} onChange={(e) => setReservationForm({ ...reservationForm, mac: e.target.value })} />
        </FormField>
        <FormField label="IP address">
          <input className="f-input font-mono" value={reservationForm.ip} onChange={(e) => setReservationForm({ ...reservationForm, ip: e.target.value })} />
        </FormField>
        <FormField label="Hostname">
          <input className="f-input" value={reservationForm.hostname} onChange={(e) => setReservationForm({ ...reservationForm, hostname: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditor(null)}>Cancel</button>
          <button className="f-btn-primary" onClick={() => addReservation.mutate()}>Add</button>
        </div>
      </SlideOver>

      <SlideOver title="Advanced subnet settings" open={editor === 'settings'} onClose={() => setEditor(null)}>
        <p className="text-table text-muted mb-3">
          Override the server defaults for this scope. Lease times are in seconds; leave a field
          empty to inherit the global default.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Lease time" hint="valid lifetime">
            <input className="f-input" type="number" min={0} placeholder="default" value={settingsForm.valid_lifetime} onChange={(e) => sf('valid_lifetime', e.target.value)} />
          </FormField>
          <FormField label="Max lease time" hint="cap on requested times">
            <input className="f-input" type="number" min={0} placeholder="auto" value={settingsForm.max_valid_lifetime} onChange={(e) => sf('max_valid_lifetime', e.target.value)} />
          </FormField>
          <FormField label="Renew timer (T1)">
            <input className="f-input" type="number" min={0} placeholder="auto" value={settingsForm.renew_timer} onChange={(e) => sf('renew_timer', e.target.value)} />
          </FormField>
          <FormField label="Rebind timer (T2)">
            <input className="f-input" type="number" min={0} placeholder="auto" value={settingsForm.rebind_timer} onChange={(e) => sf('rebind_timer', e.target.value)} />
          </FormField>
        </div>
        <FormField label="Boot server (next-server)" hint="PXE/TFTP server IP for network boot">
          <input className="f-input font-mono" placeholder="10.0.0.2" value={settingsForm.next_server} onChange={(e) => sf('next_server', e.target.value)} />
        </FormField>
        <FormField label="Boot file name" hint="Network boot file, e.g. pxelinux.0">
          <input className="f-input font-mono" placeholder="pxelinux.0" value={settingsForm.boot_file_name} onChange={(e) => sf('boot_file_name', e.target.value)} />
        </FormField>
        <FormField label="Client class" hint="Only serve this scope to clients in the named class">
          <input className="f-input font-mono" placeholder="(none)" value={settingsForm.client_class} onChange={(e) => sf('client_class', e.target.value)} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditor(null)}>Cancel</button>
          <button className="f-btn-primary" disabled={saveSettings.isPending} onClick={() => saveSettings.mutate()}>Save</button>
        </div>
      </SlideOver>

      <SlideOver title="Set Option" open={editor === 'option'} onClose={() => setEditor(null)}>
        <FormField label="Option">
          <select className="f-input" value={optionForm.name} onChange={(e) => setOptionForm({ ...optionForm, name: e.target.value })}>
            {OPTION_NAMES.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Value" hint="Comma-separate multiple values">
          <input className="f-input font-mono" value={optionForm.value} onChange={(e) => setOptionForm({ ...optionForm, value: e.target.value })} />
        </FormField>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setEditor(null)}>Cancel</button>
          <button className="f-btn-primary" onClick={() => addOption.mutate()}>Set</button>
        </div>
      </SlideOver>

      <Modal title="DHCP configuration preview" open={previewOpen} onClose={() => setPreviewOpen(false)} wide>
        <pre className="bg-slate-900 text-slate-100 rounded p-3 text-xs overflow-x-auto whitespace-pre">
          {preview?.kea_dhcp4_conf ?? 'Loading…'}
        </pre>
      </Modal>

      <ConfirmDialog
        title="Remove"
        message={`Remove ${confirm?.label}?`}
        open={confirm !== null}
        onCancel={() => setConfirm(null)}
        onConfirm={() => confirm && removeItem.mutate({ kind: confirm.kind, id: confirm.id })}
      />
    </>
  );
}
