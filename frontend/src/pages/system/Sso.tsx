import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, ShieldCheck, Plus, Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { SsoConfig } from '../../api/types';
import FormField from '../../components/FormField';
import { useToast } from '../../components/Toast';

const NAMEID_FORMATS = [
  ['urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress', 'Email address'],
  ['urn:oasis:names:tc:SAML:2.0:nameid-format:persistent', 'Persistent'],
  ['urn:oasis:names:tc:SAML:2.0:nameid-format:transient', 'Transient'],
  ['urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified', 'Unspecified'],
] as const;

type RolePair = { group: string; role: string };

export default function Sso() {
  const toast = useToast();
  const qc = useQueryClient();
  const [cfg, setCfg] = useState<SsoConfig | null>(null);
  const [pairs, setPairs] = useState<RolePair[]>([]);
  const [advanced, setAdvanced] = useState(false);
  const [spPrivateKey, setSpPrivateKey] = useState('');
  const [spCert, setSpCert] = useState('');

  const { data } = useQuery({
    queryKey: ['sso-config'],
    queryFn: () => api.get<SsoConfig>('/api/v1/sso/config'),
  });

  useEffect(() => {
    if (data) {
      setCfg(data);
      setPairs(Object.entries(data.role_mappings ?? {}).map(([group, role]) => ({ group, role })));
    }
  }, [data]);

  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.put<SsoConfig>('/api/v1/sso/config', body),
    onSuccess: (saved) => {
      toast('success', 'SSO configuration saved');
      setCfg(saved);
      qc.invalidateQueries({ queryKey: ['sso-config'] });
      qc.invalidateQueries({ queryKey: ['sso-status'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  if (!cfg) return <div className="text-muted">Loading…</div>;

  const set = (patch: Partial<SsoConfig>) => setCfg({ ...cfg, ...patch });

  const submit = () => {
    const role_mappings: Record<string, string> = {};
    pairs.forEach((p) => { if (p.group.trim()) role_mappings[p.group.trim()] = p.role; });
    const { sp_metadata_url, acs_url, sp_entity_id_effective, sp_signing_configured, ...body } = cfg;
    void sp_metadata_url; void acs_url; void sp_entity_id_effective; void sp_signing_configured;
    const extra: Record<string, unknown> = { ...body, role_mappings };
    if (spPrivateKey.trim()) extra.sp_private_key = spPrivateKey;
    if (spCert.trim()) extra.sp_x509_cert = spCert;
    save.mutate(extra);
  };

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast('success', 'Copied to clipboard');
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-lg font-semibold mb-1 flex items-center gap-2">
        <ShieldCheck size={18} /> SAML Single Sign-On
      </h1>
      <p className="text-table text-muted mb-4">
        M-Eyes acts as the SAML Service Provider (SP). Configure your IdP —
        <strong> FortiAuthenticator</strong> is recommended — then map IdP groups to M-Eyes roles.
        See the docs for a full FortiAuthenticator walkthrough.
      </p>

      <div className="f-card p-4 mb-4">
        <label className="flex items-center gap-2 text-sm font-medium mb-3">
          <input type="checkbox" checked={cfg.enabled} onChange={(e) => set({ enabled: e.target.checked })} />
          Enable SAML SSO on the login page
        </label>
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Login button label">
            <input className="f-input" value={cfg.button_label} onChange={(e) => set({ button_label: e.target.value })} />
          </FormField>
          <FormField label="M-Eyes base URL (external HTTPS)" hint="Used to build SP entity ID, ACS and metadata URLs">
            <input className="f-input font-mono" value={cfg.base_url} placeholder="https://meyes.example.com"
                   onChange={(e) => set({ base_url: e.target.value })} />
          </FormField>
        </div>
      </div>

      {/* Service Provider values to copy into the IdP */}
      <div className="f-card p-4 mb-4">
        <div className="font-semibold text-sm mb-2">Service Provider details (give these to your IdP)</div>
        {([['SP entity ID', cfg.sp_entity_id_effective], ['ACS (reply) URL', cfg.acs_url], ['SP metadata URL', cfg.sp_metadata_url]] as const).map(([label, value]) => (
          <div key={label} className="flex items-center gap-2 mb-2">
            <span className="text-xs text-muted w-36 shrink-0">{label}</span>
            <input className="f-input font-mono text-xs" readOnly value={value || '(set base URL first)'} />
            <button className="f-btn-secondary" onClick={() => copy(value)} disabled={!value}><Copy size={13} /></button>
          </div>
        ))}
      </div>

      {/* Identity Provider */}
      <div className="f-card p-4 mb-4">
        <div className="font-semibold text-sm mb-2">Identity Provider</div>
        <FormField label="IdP entity ID">
          <input className="f-input font-mono" value={cfg.idp_entity_id} onChange={(e) => set({ idp_entity_id: e.target.value })} />
        </FormField>
        <FormField label="IdP Single Sign-On URL (HTTP-Redirect)">
          <input className="f-input font-mono" value={cfg.idp_sso_url} placeholder="https://fac.example.com/saml-idp/.../login/"
                 onChange={(e) => set({ idp_sso_url: e.target.value })} />
        </FormField>
        <FormField label="IdP Single Logout URL (optional)">
          <input className="f-input font-mono" value={cfg.idp_slo_url} onChange={(e) => set({ idp_slo_url: e.target.value })} />
        </FormField>
        <FormField label="IdP signing certificate (PEM or base64)">
          <textarea className="f-input font-mono text-xs" rows={4} value={cfg.idp_x509_cert}
                    onChange={(e) => set({ idp_x509_cert: e.target.value })}
                    placeholder="-----BEGIN CERTIFICATE-----" />
        </FormField>
      </div>

      {/* Attribute + role mapping */}
      <div className="f-card p-4 mb-4">
        <div className="font-semibold text-sm mb-2">Attribute &amp; role mapping</div>
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Username attribute" hint="Blank uses the SAML NameID">
            <input className="f-input font-mono" value={cfg.attr_username} onChange={(e) => set({ attr_username: e.target.value })} />
          </FormField>
          <FormField label="Email attribute">
            <input className="f-input font-mono" value={cfg.attr_email} onChange={(e) => set({ attr_email: e.target.value })} />
          </FormField>
          <FormField label="Display-name attribute">
            <input className="f-input font-mono" value={cfg.attr_display_name} onChange={(e) => set({ attr_display_name: e.target.value })} />
          </FormField>
          <FormField label="Groups attribute" hint="Carries the group/role values">
            <input className="f-input font-mono" value={cfg.attr_groups} onChange={(e) => set({ attr_groups: e.target.value })} />
          </FormField>
        </div>

        <div className="flex items-center justify-between mt-2 mb-1">
          <span className="f-label">Group → role mappings</span>
          <button className="text-accent text-xs flex items-center gap-1" onClick={() => setPairs([...pairs, { group: '', role: 'viewer' }])}>
            <Plus size={12} /> Add mapping
          </button>
        </div>
        {pairs.map((p, idx) => (
          <div key={idx} className="flex gap-2 mb-2 items-center">
            <input className="f-input font-mono text-xs" placeholder="IdP group value" value={p.group}
                   onChange={(e) => { const n = [...pairs]; n[idx] = { ...p, group: e.target.value }; setPairs(n); }} />
            <span className="text-muted text-xs">→</span>
            <select className="f-input text-xs w-32" value={p.role}
                    onChange={(e) => { const n = [...pairs]; n[idx] = { ...p, role: e.target.value }; setPairs(n); }}>
              <option value="viewer">viewer</option>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
            <button className="text-danger" onClick={() => setPairs(pairs.filter((_, i) => i !== idx))}><Trash2 size={13} /></button>
          </div>
        ))}
        <div className="grid grid-cols-2 gap-2 mt-2">
          <FormField label="Default role (no mapping matched)">
            <select className="f-input" value={cfg.default_role} onChange={(e) => set({ default_role: e.target.value })}>
              <option value="viewer">viewer</option>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
          </FormField>
          <FormField label="Just-in-time provisioning">
            <label className="flex items-center gap-2 text-table mt-2">
              <input type="checkbox" checked={cfg.allow_jit_provisioning} onChange={(e) => set({ allow_jit_provisioning: e.target.checked })} />
              Create users automatically on first login
            </label>
          </FormField>
        </div>
      </div>

      <button className="text-accent text-sm mb-2" onClick={() => setAdvanced((v) => !v)}>
        {advanced ? 'Hide' : 'Show'} advanced settings
      </button>
      {advanced && (
        <div className="f-card p-4 mb-4">
          <div className="grid grid-cols-2 gap-2">
            <FormField label="NameID format">
              <select className="f-input" value={cfg.name_id_format} onChange={(e) => set({ name_id_format: e.target.value })}>
                {NAMEID_FORMATS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </FormField>
            <FormField label="Allowed clock skew (seconds)">
              <input className="f-input" type="number" value={cfg.allowed_clock_skew_seconds}
                     onChange={(e) => set({ allowed_clock_skew_seconds: Number(e.target.value) })} />
            </FormField>
            <FormField label="Signature algorithm">
              <select className="f-input" value={cfg.signature_algorithm} onChange={(e) => set({ signature_algorithm: e.target.value })}>
                <option value="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256">RSA-SHA256</option>
                <option value="http://www.w3.org/2000/09/xmldsig#rsa-sha1">RSA-SHA1 (legacy)</option>
              </select>
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
            {([
              ['want_assertions_signed', 'Require signed assertions'],
              ['want_response_signed', 'Require signed response'],
              ['sign_authn_requests', 'Sign AuthnRequests (needs SP keypair)'],
              ['force_authn', 'Force re-authentication (ForceAuthn)'],
            ] as const).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-table">
                <input type="checkbox" checked={Boolean(cfg[key])} onChange={(e) => set({ [key]: e.target.checked } as Partial<SsoConfig>)} />
                {label}
              </label>
            ))}
          </div>
          <FormField label="SP private key (PEM, only for signed AuthnRequests)">
            <textarea className="f-input font-mono text-xs" rows={3} value={spPrivateKey}
                      placeholder={cfg.sp_signing_configured ? '•••• stored — leave blank to keep ••••' : '-----BEGIN PRIVATE KEY-----'}
                      onChange={(e) => setSpPrivateKey(e.target.value)} />
          </FormField>
          <FormField label="SP certificate (PEM)">
            <textarea className="f-input font-mono text-xs" rows={3} value={spCert}
                      placeholder={cfg.sp_signing_configured ? '•••• stored ••••' : '-----BEGIN CERTIFICATE-----'}
                      onChange={(e) => setSpCert(e.target.value)} />
          </FormField>
        </div>
      )}

      <div className="flex justify-end gap-2">
        <a className="f-btn-secondary" href="/api/v1/sso/metadata" target="_blank" rel="noreferrer">Download SP metadata</a>
        <button className="f-btn-primary" disabled={save.isPending} onClick={submit}>Save configuration</button>
      </div>
    </div>
  );
}
