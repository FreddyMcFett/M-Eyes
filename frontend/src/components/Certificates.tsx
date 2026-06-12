import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BadgeCheck,
  Download,
  FileKey,
  FilePlus2,
  Landmark,
  Plus,
  ShieldCheck,
  Trash2,
  Upload,
} from 'lucide-react';
import { api, getToken } from '../api/client';
import { Certificate } from '../api/types';
import FormField from './FormField';
import Modal from './Modal';
import { useToast } from './Toast';

const BASE = '/api/v1/system/certificates';

interface SubjectForm {
  common_name: string;
  organization: string;
  organizational_unit: string;
  country: string;
  state: string;
  locality: string;
  email: string;
}

const emptySubject = (cn = ''): SubjectForm => ({
  common_name: cn,
  organization: '',
  organizational_unit: '',
  country: '',
  state: '',
  locality: '',
  email: '',
});

function expiryLabel(cert: Certificate): { text: string; cls: string } {
  if (!cert.not_after) return { text: '—', cls: 'text-muted' };
  const days = Math.round((new Date(cert.not_after).getTime() - Date.now()) / 86_400_000);
  if (days < 0) return { text: `expired ${-days}d ago`, cls: 'text-danger' };
  if (days < 30) return { text: `expires in ${days}d`, cls: 'text-warning' };
  return { text: `valid ${days}d`, cls: 'text-muted' };
}

function StatusPill({ cert }: { cert: Certificate }) {
  const map: Record<string, string> = {
    active: 'bg-accent/15 text-accent',
    inactive: 'bg-slate-200 text-slate-600',
    pending_csr: 'bg-warning/15 text-warning',
    trusted: 'bg-info/15 text-info',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${map[cert.status] ?? 'bg-slate-200'}`}>
      {cert.status.replace('_', ' ')}
    </span>
  );
}

export default function Certificates({ defaultCn }: { defaultCn?: string }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<'csr' | 'self' | 'ca' | 'server' | null>(null);
  const [importFor, setImportFor] = useState<Certificate | null>(null);

  const { data: certs = [] } = useQuery({
    queryKey: ['certificates'],
    queryFn: () => api.get<Certificate[]>(BASE),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['certificates'] });
    qc.invalidateQueries({ queryKey: ['tls-status'] });
  };

  const activate = useMutation({
    mutationFn: (id: number) => api.post(`${BASE}/${id}/activate`),
    onSuccess: () => {
      toast('success', 'Certificate activated for HTTPS');
      invalidate();
    },
    onError: (e: Error) => toast('error', e.message),
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`${BASE}/${id}`),
    onSuccess: () => {
      toast('success', 'Certificate deleted');
      invalidate();
    },
    onError: (e: Error) => toast('error', e.message),
  });

  const download = async (cert: Certificate, part: 'cert' | 'csr' | 'chain') => {
    const res = await fetch(`${BASE}/${cert.id}/download?part=${part}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) {
      toast('error', `Could not download ${part}`);
      return;
    }
    const text = await res.text();
    const blob = new Blob([text], { type: 'application/x-pem-file' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${cert.name.replace(/\s+/g, '_')}.${part === 'csr' ? 'csr' : 'pem'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const servers = certs.filter((c) => c.kind === 'server');
  const cas = certs.filter((c) => c.kind === 'ca');

  return (
    <div className="f-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <FileKey size={16} className="text-accent" /> Certificates
        </h3>
        <div className="flex gap-2 flex-wrap">
          <button className="f-btn-secondary" onClick={() => setDialog('csr')}>
            <FilePlus2 size={14} /> Generate CSR
          </button>
          <button className="f-btn-secondary" onClick={() => setDialog('self')}>
            <Plus size={14} /> Self-signed
          </button>
          <button className="f-btn-secondary" onClick={() => setDialog('server')}>
            <Upload size={14} /> Import cert + key
          </button>
          <button className="f-btn-secondary" onClick={() => setDialog('ca')}>
            <Landmark size={14} /> Import CA
          </button>
        </div>
      </div>

      <h4 className="text-xs font-semibold uppercase text-muted mb-1 mt-2">Server certificates</h4>
      <table className="f-table w-full text-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Subject</th>
            <th>Type</th>
            <th>Status</th>
            <th>Validity</th>
            <th className="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {servers.length === 0 && (
            <tr><td colSpan={6} className="text-muted py-3">No server certificates yet.</td></tr>
          )}
          {servers.map((c) => {
            const exp = expiryLabel(c);
            return (
              <tr key={c.id}>
                <td className="font-medium">{c.name}</td>
                <td className="font-mono text-xs">{c.subject || '—'}</td>
                <td className="text-xs">{c.key_type || '—'}{c.is_self_signed ? ' · self-signed' : ''}</td>
                <td><StatusPill cert={c} /></td>
                <td className={`text-xs ${exp.cls}`}>{exp.text}</td>
                <td>
                  <div className="flex gap-1.5 justify-end items-center">
                    {c.status === 'pending_csr' && (
                      <>
                        <button className="f-icon-btn" title="Download CSR" onClick={() => download(c, 'csr')}>
                          <Download size={14} />
                        </button>
                        <button className="f-icon-btn text-accent" title="Import signed certificate" onClick={() => setImportFor(c)}>
                          <Upload size={14} />
                        </button>
                      </>
                    )}
                    {c.has_key && c.status !== 'pending_csr' && c.status !== 'active' && (
                      <button className="f-icon-btn text-accent" title="Activate for HTTPS" onClick={() => activate.mutate(c.id)}>
                        <ShieldCheck size={14} />
                      </button>
                    )}
                    {c.status === 'active' && <BadgeCheck size={15} className="text-accent" />}
                    {c.status !== 'pending_csr' && (
                      <button className="f-icon-btn" title="Download certificate" onClick={() => download(c, 'cert')}>
                        <Download size={14} />
                      </button>
                    )}
                    <button className="f-icon-btn text-danger" title="Delete" onClick={() => remove.mutate(c.id)} disabled={c.status === 'active'}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h4 className="text-xs font-semibold uppercase text-muted mb-1 mt-4">Trusted CA certificates</h4>
      <table className="f-table w-full text-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Subject</th>
            <th>Validity</th>
            <th className="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {cas.length === 0 && (
            <tr><td colSpan={4} className="text-muted py-3">No CA certificates imported.</td></tr>
          )}
          {cas.map((c) => {
            const exp = expiryLabel(c);
            return (
              <tr key={c.id}>
                <td className="font-medium">{c.name}</td>
                <td className="font-mono text-xs">{c.subject || '—'}</td>
                <td className={`text-xs ${exp.cls}`}>{exp.text}</td>
                <td>
                  <div className="flex gap-1.5 justify-end">
                    <button className="f-icon-btn" title="Download" onClick={() => download(c, 'cert')}>
                      <Download size={14} />
                    </button>
                    <button className="f-icon-btn text-danger" title="Delete" onClick={() => remove.mutate(c.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {dialog === 'csr' && (
        <SubjectDialog
          title="Generate CSR"
          submitLabel="Generate CSR"
          defaultCn={defaultCn}
          onClose={() => setDialog(null)}
          onSubmit={async (name, subject, sans) => {
            await api.post(`${BASE}/csr`, { name, subject, sans });
            toast('success', 'CSR generated — download it and submit to your CA');
            invalidate();
          }}
        />
      )}
      {dialog === 'self' && (
        <SubjectDialog
          title="Generate self-signed certificate"
          submitLabel="Generate & activate"
          defaultCn={defaultCn}
          onClose={() => setDialog(null)}
          onSubmit={async (name, subject, sans) => {
            await api.post(`${BASE}/self-signed`, { name, subject, sans, activate: true });
            toast('success', 'Self-signed certificate created and activated');
            invalidate();
          }}
        />
      )}
      {dialog === 'ca' && (
        <PemDialog
          title="Import CA certificate"
          fields={[{ key: 'cert_pem', label: 'CA certificate (PEM)' }]}
          onClose={() => setDialog(null)}
          onSubmit={async (name, vals) => {
            await api.post(`${BASE}/ca`, { name, cert_pem: vals.cert_pem });
            toast('success', 'CA certificate added to the trust bundle');
            invalidate();
          }}
        />
      )}
      {dialog === 'server' && (
        <PemDialog
          title="Import certificate + private key"
          activatable
          fields={[
            { key: 'cert_pem', label: 'Certificate (PEM)' },
            { key: 'key_pem', label: 'Private key (PEM)' },
            { key: 'chain_pem', label: 'Intermediate chain (PEM, optional)', optional: true },
          ]}
          onClose={() => setDialog(null)}
          onSubmit={async (name, vals, activate) => {
            await api.post(`${BASE}/import-server`, {
              name,
              cert_pem: vals.cert_pem,
              key_pem: vals.key_pem,
              chain_pem: vals.chain_pem || null,
              activate,
            });
            toast('success', 'Certificate imported');
            invalidate();
          }}
        />
      )}
      {importFor && (
        <PemDialog
          title={`Import signed certificate for "${importFor.name}"`}
          activatable
          nameless
          fields={[
            { key: 'cert_pem', label: 'Signed certificate (PEM)' },
            { key: 'chain_pem', label: 'Intermediate chain (PEM, optional)', optional: true },
          ]}
          onClose={() => setImportFor(null)}
          onSubmit={async (_name, vals, activate) => {
            await api.post(`${BASE}/${importFor.id}/import-cert`, {
              cert_pem: vals.cert_pem,
              chain_pem: vals.chain_pem || null,
              activate,
            });
            toast('success', 'Signed certificate imported');
            invalidate();
          }}
        />
      )}
    </div>
  );
}

function SubjectDialog({
  title, submitLabel, defaultCn, onClose, onSubmit,
}: {
  title: string;
  submitLabel: string;
  defaultCn?: string;
  onClose: () => void;
  onSubmit: (name: string, subject: SubjectForm, sans: string[]) => Promise<void>;
}) {
  const toast = useToast();
  const [name, setName] = useState(defaultCn ? `${defaultCn} certificate` : '');
  const [subject, setSubject] = useState<SubjectForm>(emptySubject(defaultCn));
  const [sans, setSans] = useState(defaultCn ?? '');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const sanList = sans.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
      await onSubmit(name, subject, sanList);
      onClose();
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'Failed');
    } finally {
      setBusy(false);
    }
  };

  const sf = (k: keyof SubjectForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setSubject({ ...subject, [k]: e.target.value });

  return (
    <Modal title={title} open onClose={onClose}>
      <FormField label="Friendly name">
        <input className="f-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Production HTTPS" />
      </FormField>
      <FormField label="Common name (CN)" hint="The primary hostname clients connect to">
        <input className="f-input" value={subject.common_name} onChange={sf('common_name')} placeholder="ddi.example.com" />
      </FormField>
      <FormField label="Subject Alternative Names" hint="Space- or comma-separated hostnames / IPs">
        <input className="f-input" value={sans} onChange={(e) => setSans(e.target.value)} placeholder="ddi.example.com 10.0.0.5" />
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Organization (O)">
          <input className="f-input" value={subject.organization} onChange={sf('organization')} />
        </FormField>
        <FormField label="Org. unit (OU)">
          <input className="f-input" value={subject.organizational_unit} onChange={sf('organizational_unit')} />
        </FormField>
        <FormField label="Country (C)">
          <input className="f-input" value={subject.country} onChange={sf('country')} placeholder="CH" maxLength={2} />
        </FormField>
        <FormField label="State / Province (ST)">
          <input className="f-input" value={subject.state} onChange={sf('state')} />
        </FormField>
        <FormField label="Locality (L)">
          <input className="f-input" value={subject.locality} onChange={sf('locality')} />
        </FormField>
        <FormField label="Email">
          <input className="f-input" value={subject.email} onChange={sf('email')} />
        </FormField>
      </div>
      <div className="flex gap-2 justify-end mt-2">
        <button className="f-btn-secondary" onClick={onClose}>Cancel</button>
        <button className="f-btn-primary" disabled={!subject.common_name || !name || busy} onClick={submit}>{submitLabel}</button>
      </div>
    </Modal>
  );
}

interface PemField { key: string; label: string; optional?: boolean }

function PemDialog({
  title, fields, activatable, nameless, onClose, onSubmit,
}: {
  title: string;
  fields: PemField[];
  activatable?: boolean;
  nameless?: boolean;
  onClose: () => void;
  onSubmit: (name: string, values: Record<string, string>, activate: boolean) => Promise<void>;
}) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [activate, setActivate] = useState(true);
  const [busy, setBusy] = useState(false);

  const onFile = (key: string) => async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setValues((v) => ({ ...v, [key]: text }));
  };

  const submit = async () => {
    setBusy(true);
    try {
      await onSubmit(name, values, activate);
      onClose();
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Failed');
    } finally {
      setBusy(false);
    }
  };

  const missingRequired = fields.some((f) => !f.optional && !values[f.key]?.trim());

  return (
    <Modal title={title} open onClose={onClose} wide>
      {!nameless && (
        <FormField label="Friendly name">
          <input className="f-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Production HTTPS" />
        </FormField>
      )}
      {fields.map((f) => (
        <FormField key={f.key} label={f.label}>
          <textarea
            className="f-input font-mono text-xs h-28"
            value={values[f.key] ?? ''}
            onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
            placeholder="-----BEGIN ...-----"
          />
          <input type="file" className="text-xs mt-1" accept=".pem,.crt,.cer,.key,.txt" onChange={onFile(f.key)} />
        </FormField>
      ))}
      {activatable && (
        <label className="flex items-center gap-2 text-table mb-2">
          <input type="checkbox" checked={activate} onChange={(e) => setActivate(e.target.checked)} />
          Activate immediately for HTTPS
        </label>
      )}
      <div className="flex gap-2 justify-end mt-2">
        <button className="f-btn-secondary" onClick={onClose}>Cancel</button>
        <button className="f-btn-primary" disabled={(!nameless && !name) || missingRequired || busy} onClick={submit}>Import</button>
      </div>
    </Modal>
  );
}
