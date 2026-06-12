import { useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Activity, Bug, KeyRound, Radio } from 'lucide-react';
import { api } from '../api/client';
import FormField from '../components/FormField';
import { useToast } from '../components/Toast';

interface SettingsValues {
  values: Record<string, string>;
}

export default function Settings() {
  const toast = useToast();
  const [values, setValues] = useState<Record<string, string>>({});
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });

  const { data } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => api.get<SettingsValues>('/api/v1/system/settings'),
  });

  useEffect(() => {
    if (data) setValues(data.values);
  }, [data]);

  const saveSettings = useMutation({
    mutationFn: () => api.put('/api/v1/system/settings', { values }),
    onSuccess: () => toast('success', 'Settings saved and applied'),
    onError: (err: Error) => toast('error', err.message),
  });

  const syslogTest = useMutation({
    mutationFn: () => api.post<{ status: string; detail: string }>('/api/v1/system/syslog-test'),
    onSuccess: (result) =>
      toast(result.status === 'sent' ? 'success' : 'error', result.detail),
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

  return (
    <>
      <h1 className="text-lg font-semibold mb-3">System — Settings</h1>
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Syslog */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Radio size={16} className="text-accent" /> Advanced Logging — Syslog Forwarding</h3>
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
            <button className="f-btn-primary" onClick={() => saveSettings.mutate()} disabled={saveSettings.isPending}>Save</button>
            <button className="f-btn-secondary" onClick={() => syslogTest.mutate()} disabled={syslogTest.isPending}>Send test message</button>
          </div>
        </div>

        {/* Debug */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><Bug size={16} className="text-warning" /> Debug Options</h3>
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
            <button className="f-btn-primary" onClick={() => saveSettings.mutate()} disabled={saveSettings.isPending}>Save</button>
            <button className="f-btn-secondary" onClick={() => pingEngine.mutate('bind')}>
              <Activity size={14} /> Test BIND
            </button>
            <button className="f-btn-secondary" onClick={() => pingEngine.mutate('kea')}>
              <Activity size={14} /> Test Kea
            </button>
            <button className="f-btn-secondary" onClick={downloadDiagnostics}>Download diagnostics</button>
          </div>
        </div>

        {/* Password */}
        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2"><KeyRound size={16} className="text-info" /> Change Password</h3>
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
      </div>
    </>
  );
}
