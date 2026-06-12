import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Bug,
  KeyRound,
  Lock,
  Radio,
  Server,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import { api } from '../api/client';
import { TlsStatus } from '../api/types';
import Certificates from '../components/Certificates';
import FormField from '../components/FormField';
import { useToast } from '../components/Toast';

interface SettingsValues {
  values: Record<string, string>;
}

type Tab = 'system' | 'https' | 'logging' | 'security';

const TABS: { id: Tab; label: string; icon: JSX.Element }[] = [
  { id: 'system', label: 'System', icon: <SlidersHorizontal size={14} /> },
  { id: 'https', label: 'HTTPS / TLS', icon: <Lock size={14} /> },
  { id: 'logging', label: 'Logging & Debug', icon: <Radio size={14} /> },
  { id: 'security', label: 'Security', icon: <KeyRound size={14} /> },
];

export default function Settings() {
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('system');
  const [values, setValues] = useState<Record<string, string>>({});
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });

  const { data } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => api.get<SettingsValues>('/api/v1/system/settings'),
  });
  const { data: tls } = useQuery({
    queryKey: ['tls-status'],
    queryFn: () => api.get<TlsStatus>('/api/v1/system/certificates/status'),
  });

  useEffect(() => {
    if (data) setValues(data.values);
  }, [data]);

  const saveSettings = useMutation({
    mutationFn: () => api.put('/api/v1/system/settings', { values }),
    onSuccess: () => {
      toast('success', 'Settings saved and applied');
      qc.invalidateQueries({ queryKey: ['tls-status'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const syslogTest = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>('/api/v1/system/syslog-test'),
    onSuccess: (result) => toast(result.status === 'sent' ? 'success' : 'error', result.detail),
    onError: (err: Error) => toast('error', err.message),
  });

  const pingEngine = useMutation({
    mutationFn: (target: string) =>
      api.get<{ reachable: boolean; latency_ms?: number; detail: string }>(`/api/v1/deploy/ping/${target}`),
    onSuccess: (result, target) =>
      toast(
        result.reachable ? 'success' : 'error',
        `${target.toUpperCase()}: ${result.reachable ? `reachable (${result.latency_ms ?? '?'} ms)` : `unreachable — ${result.detail}`}`,
      ),
  });

  const changePassword = useMutation({
    mutationFn: () =>
      api.post('/api/v1/auth/change-password', {
        current_password: passwords.current,
        new_password: passwords.next,
      }),
    onSuccess: () => {
      toast('success', 'Password changed');
      setPasswords({ current: '', next: '', confirm: '' });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const downloadDiagnostics = async () => {
    try {
      const diagnostics = await api.get('/api/v1/system/diagnostics');
      const blob = new Blob([JSON.stringify(diagnostics, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'm-eyes-diagnostics.json';
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Failed');
    }
  };

  const set = (key: string, value: string) => setValues((v) => ({ ...v, [key]: value }));
  const boolToggle = (key: string) => (
    <input
      type="checkbox"
      checked={values[key] === 'true'}
      onChange={(e) => set(key, e.target.checked ? 'true' : 'false')}
    />
  );

  const SaveBtn = () => (
    <button className="f-btn-primary" onClick={() => saveSettings.mutate()} disabled={saveSettings.isPending}>
      Save
    </button>
  );

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">System — Settings</h1>

      <div className="flex gap-1 border-b border-line mb-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 text-table border-b-2 -mb-px ${
              tab === t.id ? 'border-accent text-accent font-medium' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'system' && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Server size={16} className="text-accent" /> System Identity
            </h3>
            <FormField label="Hostname (FQDN)" hint="How clients reach M-Eyes; default CN/SAN for generated certificates">
              <input className="f-input" value={values.system_hostname ?? ''} onChange={(e) => set('system_hostname', e.target.value)} placeholder="ddi.example.com" />
            </FormField>
            <FormField label="Organization" hint="Default Organization (O) field in generated CSRs">
              <input className="f-input" value={values.organization_name ?? ''} onChange={(e) => set('organization_name', e.target.value)} placeholder="Example Corp" />
            </FormField>
            <SaveBtn />
          </div>

          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Bug size={16} className="text-warning" /> Debug & Diagnostics
            </h3>
            <FormField label="Debug mode" hint="Includes raw rndc / Kea Control Agent output in deploy responses">
              <label className="flex items-center gap-2 text-table">{boolToggle('debug_mode')} Enabled</label>
            </FormField>
            <FormField label="Application log level">
              <select className="f-input" value={values.log_level ?? 'info'} onChange={(e) => set('log_level', e.target.value)}>
                {['debug', 'info', 'warning', 'error'].map((level) => (
                  <option key={level} value={level}>{level}</option>
                ))}
              </select>
            </FormField>
            <div className="flex gap-2 flex-wrap">
              <SaveBtn />
              <button className="f-btn-secondary" onClick={() => pingEngine.mutate('bind')}><Activity size={14} /> Test BIND</button>
              <button className="f-btn-secondary" onClick={() => pingEngine.mutate('kea')}><Activity size={14} /> Test Kea</button>
              <button className="f-btn-secondary" onClick={downloadDiagnostics}>Download diagnostics</button>
            </div>
          </div>
        </div>
      )}

      {tab === 'https' && (
        <div className="grid gap-4">
          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <ShieldCheck size={16} className="text-accent" /> HTTPS Status
            </h3>
            {tls?.https_ready ? (
              <div className="text-table">
                <span className="px-2 py-0.5 rounded bg-accent/15 text-accent text-xs font-medium">HTTPS active</span>
                {tls.active_certificate && (
                  <div className="mt-2 text-xs text-slate-600">
                    <div><span className="text-muted">Serving:</span> <span className="font-mono">{tls.active_certificate.subject}</span></div>
                    <div><span className="text-muted">Issuer:</span> <span className="font-mono">{tls.active_certificate.issuer}</span></div>
                    <div><span className="text-muted">SHA-256:</span> <span className="font-mono break-all">{tls.active_certificate.fingerprint_sha256}</span></div>
                    {tls.active_certificate.not_after && (
                      <div><span className="text-muted">Expires:</span> {new Date(tls.active_certificate.not_after).toLocaleString()}</div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-table text-warning">No active certificate — a self-signed certificate is generated automatically on first start.</p>
            )}
          </div>

          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Lock size={16} className="text-info" /> TLS Options
            </h3>
            <div className="grid md:grid-cols-3 gap-3">
              <FormField label="Redirect HTTP → HTTPS">
                <label className="flex items-center gap-2 text-table">{boolToggle('https_redirect')} Enabled</label>
              </FormField>
              <FormField label="HSTS" hint="Strict-Transport-Security header">
                <label className="flex items-center gap-2 text-table">{boolToggle('hsts_enabled')} Enabled</label>
              </FormField>
              <FormField label="Minimum TLS version">
                <select className="f-input" value={values.tls_min_version ?? 'TLSv1.2'} onChange={(e) => set('tls_min_version', e.target.value)}>
                  <option value="TLSv1.2">TLS 1.2</option>
                  <option value="TLSv1.3">TLS 1.3</option>
                </select>
              </FormField>
            </div>
            <div className="mt-1"><SaveBtn /></div>
          </div>

          <Certificates defaultCn={values.system_hostname || tls?.settings.system_hostname} />
        </div>
      )}

      {tab === 'logging' && (
        <div className="f-card p-4 max-w-2xl">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <Radio size={16} className="text-accent" /> Advanced Logging — Syslog Forwarding
          </h3>
          <FormField label="Forward events to syslog">
            <label className="flex items-center gap-2 text-table">{boolToggle('syslog_enabled')} Enabled</label>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Syslog server">
              <input className="f-input" value={values.syslog_host ?? ''} onChange={(e) => set('syslog_host', e.target.value)} placeholder="fortianalyzer.example.com" />
            </FormField>
            <FormField label="Port">
              <input className="f-input" type="number" value={values.syslog_port ?? '514'} onChange={(e) => set('syslog_port', e.target.value)} />
            </FormField>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <FormField label="Protocol">
              <select className="f-input" value={values.syslog_protocol ?? 'udp'} onChange={(e) => set('syslog_protocol', e.target.value)}>
                <option value="udp">UDP</option>
                <option value="tcp">TCP</option>
              </select>
            </FormField>
            <FormField label="Facility">
              <select className="f-input" value={values.syslog_facility ?? 'local0'} onChange={(e) => set('syslog_facility', e.target.value)}>
                {['local0', 'local1', 'local2', 'local3', 'local4', 'local5', 'local6', 'local7', 'daemon', 'syslog'].map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Min severity">
              <select className="f-input" value={values.syslog_min_severity ?? 'info'} onChange={(e) => set('syslog_min_severity', e.target.value)}>
                {['debug', 'info', 'warning', 'error'].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </FormField>
          </div>
          <div className="flex gap-2">
            <SaveBtn />
            <button className="f-btn-secondary" onClick={() => syslogTest.mutate()} disabled={syslogTest.isPending}>Send test message</button>
          </div>
        </div>
      )}

      {tab === 'security' && (
        <div className="f-card p-4 max-w-lg">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <KeyRound size={16} className="text-info" /> Change Password
          </h3>
          <FormField label="Current password">
            <input className="f-input" type="password" value={passwords.current} onChange={(e) => setPasswords({ ...passwords, current: e.target.value })} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="New password">
              <input className="f-input" type="password" value={passwords.next} onChange={(e) => setPasswords({ ...passwords, next: e.target.value })} />
            </FormField>
            <FormField label="Confirm">
              <input className="f-input" type="password" value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} />
            </FormField>
          </div>
          <button
            className="f-btn-primary"
            disabled={!passwords.current || !passwords.next || passwords.next !== passwords.confirm || changePassword.isPending}
            onClick={() => changePassword.mutate()}
          >
            Change password
          </button>
          {passwords.next && passwords.confirm && passwords.next !== passwords.confirm && (
            <p className="text-danger text-xs mt-2">Passwords do not match</p>
          )}
        </div>
      )}
    </>
  );
}
