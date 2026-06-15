import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  Bug,
  CheckCircle2,
  Copy,
  DatabaseBackup,
  DownloadCloud,
  Globe,
  KeyRound,
  Loader2,
  Lock,
  Radio,
  RefreshCw,
  RotateCw,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';
import { api } from '../api/client';
import { ApiKey, TlsStatus, UpdateProgress, UpdateStatus } from '../api/types';
import Certificates from '../components/Certificates';
import ConfirmDialog from '../components/ConfirmDialog';
import FormField from '../components/FormField';
import { useToast } from '../components/Toast';

interface SettingsValues {
  values: Record<string, string>;
}

type Tab = 'system' | 'services' | 'https' | 'logging' | 'security' | 'maintenance';

const TABS: { id: Tab; label: string; icon: JSX.Element }[] = [
  { id: 'system', label: 'System', icon: <SlidersHorizontal size={14} /> },
  { id: 'services', label: 'DNS & DHCP', icon: <Server size={14} /> },
  { id: 'https', label: 'HTTPS / TLS', icon: <Lock size={14} /> },
  { id: 'logging', label: 'Logging & Debug', icon: <Radio size={14} /> },
  { id: 'security', label: 'Security', icon: <KeyRound size={14} /> },
  { id: 'maintenance', label: 'Backup & Updates', icon: <DatabaseBackup size={14} /> },
];

export default function Settings() {
  const toast = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('system');
  const [values, setValues] = useState<Record<string, string>>({});
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
  const [keyForm, setKeyForm] = useState({ name: '', expires_in_days: '' });
  const [createdKey, setCreatedKey] = useState<ApiKey | null>(null);
  const [deletingKey, setDeletingKey] = useState<ApiKey | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState<Record<string, unknown> | null>(null);
  const restoreInput = useRef<HTMLInputElement>(null);
  const [updateConfirm, setUpdateConfirm] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [progress, setProgress] = useState<UpdateProgress | null>(null);
  const [updateDone, setUpdateDone] = useState(false);
  const targetVersion = useRef<string | null>(null);

  const { data } = useQuery({
    queryKey: ['app-settings'],
    queryFn: () => api.get<SettingsValues>('/api/v1/system/settings'),
  });
  const { data: timezones } = useQuery({
    queryKey: ['timezones'],
    queryFn: () => api.get<{ timezones: string[] }>('/api/v1/system/timezones'),
    enabled: tab === 'system',
    staleTime: Infinity,
  });
  const { data: tls } = useQuery({
    queryKey: ['tls-status'],
    queryFn: () => api.get<TlsStatus>('/api/v1/system/certificates/status'),
  });

  const { data: apiKeys = [] } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.get<ApiKey[]>('/api/v1/apikeys'),
    enabled: tab === 'security',
  });
  const {
    data: updateStatus,
    isError: updateCheckFailed,
    isFetching: updateChecking,
    refetch: refetchUpdate,
  } = useQuery({
    queryKey: ['update-check'],
    queryFn: () => api.get<UpdateStatus>('/api/v1/system/update-check'),
    enabled: tab === 'maintenance',
    retry: 1,
  });
  // A always-reachable source for the installed version, so the panel can still
  // show "you are on vX" even if the update-server lookup cannot complete.
  const { data: systemInfo } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => api.get<{ version: string }>('/api/v1/system/info'),
    enabled: tab === 'maintenance',
  });
  const installedVersion = updateStatus?.current_version ?? systemInfo?.version ?? null;

  useEffect(() => {
    if (data) setValues(data.values);
  }, [data]);

  // Poll the update progress while an update is running. The API restarts as
  // part of the update, so unreachable polls are expected and treated as
  // "restarting" rather than a failure. Success is detected when the (now
  // restarted) API reports the target version as its running version.
  useEffect(() => {
    if (!updating) return;
    let active = true;
    const poll = async () => {
      try {
        const s = await api.get<UpdateProgress>('/api/v1/system/update/status');
        if (!active) return;
        setProgress(s);
        const target = targetVersion.current;
        if (s.phase === 'error') {
          setUpdating(false);
        } else if (target && s.current_version === target) {
          setUpdating(false);
          setUpdateDone(true);
        }
      } catch {
        // API is restarting / briefly unreachable — show a "restarting" state.
        if (!active) return;
        setProgress((p) => ({
          ...(p ?? { target_version: targetVersion.current }),
          phase: 'recreating',
          message: 'Restarting M-Eyes …',
        } as UpdateProgress));
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [updating]);

  const checkUpdates = useMutation({
    mutationFn: () => api.get<UpdateStatus>('/api/v1/system/update-check?force=true'),
    onSuccess: (s) => {
      qc.setQueryData(['update-check'], s);
      if (s.error) {
        toast('error', s.error);
      } else if (s.update_available) {
        toast('success', `Update available: v${s.latest_version}`);
      } else if (s.pending_images) {
        toast(
          'success',
          `v${s.latest_version} was just released — its container images are still publishing. Try again in a few minutes.`,
        );
      } else {
        toast('success', `You are on the latest version (v${s.current_version})`);
      }
    },
    onError: () =>
      toast('error', 'Could not reach the update server — check this system’s network access.'),
  });

  const triggerUpdate = useMutation({
    mutationFn: () => api.post<UpdateProgress>('/api/v1/system/update'),
    onSuccess: (s) => {
      targetVersion.current = s.target_version;
      setProgress(s);
      setUpdateDone(false);
      setUpdating(true);
      setUpdateConfirm(false);
    },
    onError: (err: Error) => {
      toast('error', err.message);
      setUpdateConfirm(false);
    },
  });

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
    onSuccess: (result, target) => {
      const label = target === 'bind' ? 'DNS engine' : 'DHCP engine';
      toast(
        result.reachable ? 'success' : 'error',
        `${label}: ${result.reachable ? `reachable (${result.latency_ms ?? '?'} ms)` : `unreachable — ${result.detail}`}`,
      );
    },
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

  const createKey = useMutation({
    mutationFn: () =>
      api.post<ApiKey>('/api/v1/apikeys', {
        name: keyForm.name,
        expires_in_days: keyForm.expires_in_days ? Number(keyForm.expires_in_days) : null,
      }),
    onSuccess: (key) => {
      setCreatedKey(key);
      setKeyForm({ name: '', expires_in_days: '' });
      qc.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const deleteKey = useMutation({
    mutationFn: (key: ApiKey) => api.delete(`/api/v1/apikeys/${key.id}`),
    onSuccess: () => {
      toast('success', 'API key revoked');
      setDeletingKey(null);
      qc.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const restore = useMutation({
    mutationFn: (backup: Record<string, unknown>) => api.post('/api/v1/system/restore', backup),
    onSuccess: () => {
      toast('success', 'Configuration restored — review and deploy to the engines');
      setRestoreConfirm(null);
      qc.invalidateQueries();
    },
    onError: (err: Error) => {
      toast('error', err.message);
      setRestoreConfirm(null);
    },
  });

  const downloadBackup = async () => {
    try {
      const backup = await api.get('/api/v1/system/backup');
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `m-eyes-backup-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Failed');
    }
  };

  const onRestoreFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      if (parsed?.format !== 'm-eyes-backup') throw new Error('Not an M-Eyes backup file');
      setRestoreConfirm(parsed);
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not read the backup file');
    } finally {
      if (restoreInput.current) restoreInput.current.value = '';
    }
  };

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

  const PHASE_LABEL: Record<string, string> = {
    requested: 'Queued …',
    pulling: 'Downloading new version …',
    recreating: 'Restarting services …',
    done: 'Finishing up …',
    error: 'Update failed',
  };

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
            <FormField label="Time zone" hint="IANA zone used to display times across the dashboards">
              <select className="f-input" value={values.timezone ?? 'UTC'} onChange={(e) => set('timezone', e.target.value)}>
                {!(timezones?.timezones ?? []).includes(values.timezone ?? 'UTC') && values.timezone && (
                  <option value={values.timezone}>{values.timezone}</option>
                )}
                {(timezones?.timezones ?? ['UTC']).map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </FormField>
            <SaveBtn />
          </div>

          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Bug size={16} className="text-warning" /> Debug & Diagnostics
            </h3>
            <FormField label="Debug mode" hint="Includes raw DNS/DHCP control-channel output in deploy responses">
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
              <button className="f-btn-secondary" onClick={() => pingEngine.mutate('bind')}><Activity size={14} /> Test DNS</button>
              <button className="f-btn-secondary" onClick={() => pingEngine.mutate('kea')}><Activity size={14} /> Test DHCP</button>
              <button className="f-btn-secondary" onClick={downloadDiagnostics}>Download diagnostics</button>
            </div>
          </div>
        </div>
      )}

      {tab === 'services' && (
        <div className="grid lg:grid-cols-2 gap-4 items-start">
          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-1 flex items-center gap-2">
              <Server size={16} className="text-accent" /> DHCP Lease Defaults
            </h3>
            <p className="text-table text-muted mb-3">
              Server-wide lease timing applied to every scope. Individual scopes can override
              these from their detail page. Times are in seconds; leave a timer empty to let the
              service derive it from the lease time.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <FormField label="Default lease time" hint="valid lifetime — how long a lease is held">
                <input className="f-input" type="number" min={60} value={values.dhcp_valid_lifetime ?? '4000'}
                       onChange={(e) => set('dhcp_valid_lifetime', e.target.value)} placeholder="4000" />
              </FormField>
              <FormField label="Maximum lease time" hint="cap on client-requested lease times (optional)">
                <input className="f-input" type="number" min={0} value={values.dhcp_max_valid_lifetime ?? ''}
                       onChange={(e) => set('dhcp_max_valid_lifetime', e.target.value)} placeholder="auto" />
              </FormField>
              <FormField label="Renew timer (T1)" hint="when clients begin renewing (optional)">
                <input className="f-input" type="number" min={0} value={values.dhcp_renew_timer ?? ''}
                       onChange={(e) => set('dhcp_renew_timer', e.target.value)} placeholder="auto" />
              </FormField>
              <FormField label="Rebind timer (T2)" hint="when clients begin rebinding (optional)">
                <input className="f-input" type="number" min={0} value={values.dhcp_rebind_timer ?? ''}
                       onChange={(e) => set('dhcp_rebind_timer', e.target.value)} placeholder="auto" />
              </FormField>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <SaveBtn />
              <span className="text-xs text-muted">Deploy DHCP afterwards to apply the change.</span>
            </div>
          </div>

          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-1 flex items-center gap-2">
              <Globe size={16} className="text-info" /> DNS Server Behaviour
            </h3>
            <p className="text-table text-muted mb-2">
              Advanced DNS controls are configured per zone, where they belong:
            </p>
            <ul className="text-table text-muted list-disc pl-5 space-y-1">
              <li><strong>Access control</strong> — allow-query, allow-transfer and dynamic-update ACLs.</li>
              <li><strong>Notifications</strong> — also-notify targets for secondary servers.</li>
              <li><strong>Forwarding</strong> — forward-first vs forward-only on forward zones.</li>
              <li><strong>SOA &amp; TTLs</strong> — refresh / retry / expire / minimum and DNSSEC signing.</li>
            </ul>
            <p className="text-table text-muted mt-2">
              Open any zone under <strong>DNS → Zones</strong> and choose <strong>Edit zone</strong> to set these.
            </p>
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
        <div className="grid lg:grid-cols-2 gap-4 items-start">
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

        <div className="f-card p-4">
          <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
            <KeyRound size={16} className="text-accent" /> API Keys
          </h3>
          <p className="text-table text-muted mb-3">
            Service-account keys for automation (Terraform, Ansible, scripts). Authenticate with
            the <code className="font-mono text-xs">X-API-Key</code> header. The full key is shown
            only once, at creation.
          </p>
          {createdKey && (
            <div className="border border-accent rounded p-3 mb-3 bg-accent/5">
              <div className="text-xs font-medium mb-1">Key “{createdKey.name}” created — copy it now, it will not be shown again:</div>
              <div className="flex items-center gap-2">
                <code className="font-mono text-xs break-all flex-1">{createdKey.key}</code>
                <button
                  className="f-btn-secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(createdKey.key ?? '');
                    toast('success', 'Key copied to clipboard');
                  }}
                >
                  <Copy size={13} /> Copy
                </button>
              </div>
            </div>
          )}
          <table className="w-full text-table mb-3">
            <thead>
              <tr className="text-left text-xs text-muted border-b border-line">
                <th className="py-1.5">Name</th>
                <th>Key</th>
                <th>Expires</th>
                <th>Last used</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map((key) => (
                <tr key={key.id} className="border-b border-line">
                  <td className="py-1.5 font-medium">{key.name}</td>
                  <td className="font-mono text-xs">{key.prefix}…</td>
                  <td>{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'never'}</td>
                  <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleString() : '—'}</td>
                  <td className="text-right">
                    <button onClick={() => setDeletingKey(key)} className="text-danger hover:opacity-70" title="Revoke">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {apiKeys.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-2 text-muted text-xs">No API keys yet</td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Key name">
              <input className="f-input" value={keyForm.name} onChange={(e) => setKeyForm({ ...keyForm, name: e.target.value })} placeholder="terraform" />
            </FormField>
            <FormField label="Expires in (days)" hint="Empty = never">
              <input className="f-input" type="number" min={1} value={keyForm.expires_in_days} onChange={(e) => setKeyForm({ ...keyForm, expires_in_days: e.target.value })} />
            </FormField>
          </div>
          <button className="f-btn-primary" disabled={!keyForm.name || createKey.isPending} onClick={() => createKey.mutate()}>
            Create API key
          </button>
        </div>
        </div>
      )}

      {tab === 'maintenance' && (
        <div className="grid lg:grid-cols-2 gap-4 items-start">
          <div className="f-card p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <DatabaseBackup size={16} className="text-accent" /> Configuration Backup
            </h3>
            <p className="text-table text-muted mb-3">
              Downloads the entire configuration (networks, zones, records, DHCP, firewall rules,
              feeds, settings and the change log) as a single JSON file. User accounts and TLS
              private keys are excluded. Restoring <strong>replaces</strong> the current
              configuration.
            </p>
            <div className="flex gap-2 flex-wrap">
              <button className="f-btn-primary" onClick={downloadBackup}>
                <DatabaseBackup size={14} /> Download backup
              </button>
              <button className="f-btn-secondary" onClick={() => restoreInput.current?.click()} disabled={restore.isPending}>
                Restore from file…
              </button>
              <input
                ref={restoreInput}
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(e) => onRestoreFile(e.target.files?.[0])}
              />
            </div>
          </div>

          <div className="f-card p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Server size={16} className="text-info" /> Software Updates
              </h3>
              <button
                className="f-btn-secondary"
                onClick={() => checkUpdates.mutate()}
                disabled={checkUpdates.isPending || updating}
              >
                <RefreshCw size={13} className={checkUpdates.isPending ? 'animate-spin' : ''} /> Check now
              </button>
            </div>
            {installedVersion === null && updateChecking ? (
              <p className="text-table text-muted">Checking for updates…</p>
            ) : (
              <div className="text-table">
                <div className="mb-1">
                  <span className="text-muted">Installed:</span>{' '}
                  <span className="font-mono">v{installedVersion ?? '…'}</span>
                </div>
                <div className="mb-2">
                  <span className="text-muted">Latest release:</span>{' '}
                  <span className="font-mono">{updateStatus?.latest_version ? `v${updateStatus.latest_version}` : 'unknown'}</span>
                </div>

                {updateDone ? (
                  <div className="border border-accent rounded p-3 bg-accent/5">
                    <div className="font-medium text-sm mb-1 flex items-center gap-1.5 text-accent">
                      <CheckCircle2 size={15} /> Update complete
                    </div>
                    <p className="text-xs text-muted mb-2">
                      M-Eyes is now running v{progress?.current_version ?? targetVersion.current}.
                      Reload to load the new interface.
                    </p>
                    <button className="f-btn-primary" onClick={() => window.location.reload()}>
                      <RotateCw size={14} /> Reload now
                    </button>
                  </div>
                ) : updating ? (
                  <div className="border border-info rounded p-3 bg-info/5">
                    <div className="font-medium text-sm mb-1 flex items-center gap-1.5">
                      <Loader2 size={15} className="animate-spin text-info" />
                      {PHASE_LABEL[progress?.phase ?? 'requested'] ?? 'Updating …'}
                    </div>
                    <p className="text-xs text-muted mb-2">
                      Updating to v{targetVersion.current}. The interface is briefly unavailable
                      while the services restart — this page reconnects automatically. Your data
                      is preserved; schema migrations run on start.
                    </p>
                    {progress?.log_tail && (
                      <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap">
                        {progress.log_tail.trim()}
                      </pre>
                    )}
                  </div>
                ) : progress?.phase === 'error' ? (
                  <div className="border border-danger rounded p-3 bg-danger/5">
                    <div className="font-medium text-sm mb-1 flex items-center gap-1.5 text-danger">
                      <AlertTriangle size={15} /> Update failed
                    </div>
                    <p className="text-xs text-muted mb-2">{progress.message || 'The update did not complete.'}</p>
                    {progress.log_tail && (
                      <pre className="text-[11px] font-mono bg-slate-900 text-slate-100 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap mb-2">
                        {progress.log_tail.trim()}
                      </pre>
                    )}
                    {updateStatus?.release_url && (
                      <a href={updateStatus.release_url} target="_blank" rel="noreferrer" className="text-info text-xs hover:underline">
                        Release notes →
                      </a>
                    )}
                  </div>
                ) : updateCheckFailed || updateStatus?.error ? (
                  <div className="border border-warning rounded p-3 bg-warning/5">
                    <div className="font-medium text-sm mb-1 flex items-center gap-1.5 text-warning">
                      <AlertTriangle size={15} /> Couldn’t check for updates
                    </div>
                    <p className="text-xs text-muted mb-2">
                      {updateStatus?.error ??
                        'Could not reach the update server — check this system’s network access.'}{' '}
                      You can still upgrade manually on the host:
                    </p>
                    <pre className="text-xs font-mono bg-slate-900 text-slate-100 p-2 rounded mb-2">{'docker compose pull\ndocker compose up -d'}</pre>
                    <div className="flex items-center gap-3">
                      <button className="f-btn-secondary" onClick={() => refetchUpdate()} disabled={updateChecking}>
                        <RefreshCw size={13} className={updateChecking ? 'animate-spin' : ''} /> Retry check
                      </button>
                      {updateStatus?.release_url && (
                        <a href={updateStatus.release_url} target="_blank" rel="noreferrer" className="text-info text-xs hover:underline">
                          Release notes →
                        </a>
                      )}
                    </div>
                  </div>
                ) : updateStatus?.update_available ? (
                  <div className="border border-warning rounded p-3 bg-warning/5">
                    <div className="font-medium text-sm mb-1">Update available</div>
                    <p className="text-xs text-muted mb-2">
                      Data is preserved across upgrades: the database lives in a persistent volume
                      and schema migrations run automatically on start.
                    </p>
                    {updateStatus?.in_app_update ? (
                      <div className="flex items-center gap-2 flex-wrap">
                        <button className="f-btn-primary" onClick={() => setUpdateConfirm(true)}>
                          <DownloadCloud size={14} /> Update now & restart
                        </button>
                        {updateStatus?.release_url && (
                          <a href={updateStatus.release_url} target="_blank" rel="noreferrer" className="text-info text-xs hover:underline">
                            Release notes →
                          </a>
                        )}
                      </div>
                    ) : (
                      <>
                        <p className="text-xs text-muted mb-2">
                          In-app update is unavailable on this deployment. Upgrade on the host:
                        </p>
                        <pre className="text-xs font-mono bg-slate-900 text-slate-100 p-2 rounded mb-2">{'docker compose pull\ndocker compose up -d'}</pre>
                        {updateStatus?.release_url && (
                          <a href={updateStatus.release_url} target="_blank" rel="noreferrer" className="text-info text-xs hover:underline">
                            Release notes →
                          </a>
                        )}
                      </>
                    )}
                  </div>
                ) : updateStatus?.pending_images ? (
                  <div className="border border-info rounded p-3 bg-info/5">
                    <div className="font-medium text-sm mb-1 flex items-center gap-1.5">
                      <Loader2 size={15} className="animate-spin text-info" />
                      v{updateStatus.latest_version} is publishing
                    </div>
                    <p className="text-xs text-muted mb-2">
                      v{updateStatus.latest_version} was just released, but its container images are
                      still being built and aren’t available to download yet. This usually takes a
                      few minutes — check again shortly.
                    </p>
                    <div className="flex items-center gap-3">
                      <button className="f-btn-secondary" onClick={() => checkUpdates.mutate()} disabled={checkUpdates.isPending || updateChecking}>
                        <RefreshCw size={13} className={checkUpdates.isPending || updateChecking ? 'animate-spin' : ''} /> Check again
                      </button>
                      {updateStatus?.release_url && (
                        <a href={updateStatus.release_url} target="_blank" rel="noreferrer" className="text-info text-xs hover:underline">
                          Release notes →
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-accent/15 text-accent text-xs font-medium">Up to date</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        title="Restore configuration"
        message={`Replace the ENTIRE current configuration with this backup${
          restoreConfirm?.created_at ? ` (created ${String(restoreConfirm.created_at)})` : ''
        }? This cannot be undone — consider downloading a backup of the current state first.`}
        open={restoreConfirm !== null}
        onCancel={() => setRestoreConfirm(null)}
        onConfirm={() => restoreConfirm && restore.mutate(restoreConfirm)}
      />

      <ConfirmDialog
        title="Revoke API key"
        message={`Revoke the API key ${deletingKey?.name}? Clients using it will lose access immediately.`}
        open={deletingKey !== null}
        onCancel={() => setDeletingKey(null)}
        onConfirm={() => deletingKey && deleteKey.mutate(deletingKey)}
      />

      <ConfirmDialog
        title="Update & restart M-Eyes"
        message={`Download v${updateStatus?.latest_version} and restart the M-Eyes services now? The web interface will be briefly unavailable while it restarts. Your configuration is preserved and database migrations run automatically on start.`}
        open={updateConfirm}
        onCancel={() => setUpdateConfirm(false)}
        onConfirm={() => triggerUpdate.mutate()}
      />
    </>
  );
}
