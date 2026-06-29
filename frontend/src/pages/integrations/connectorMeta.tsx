import {
  BarChart3,
  Fingerprint,
  Globe,
  Network,
  Plug,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';

/* --------------------------------------------------------------------------
   Visual identity for enterprise connectors — a representative icon and a
   brand-ish accent per connector kind, plus a branded header per category.
   Kept in one place so the picker tiles, the table and any future surface stay
   consistent.
   -------------------------------------------------------------------------- */

export interface ConnectorVisual {
  Icon: typeof Plug;
  color: string;
}

const CONNECTORS: Record<string, ConnectorVisual> = {
  fortigate: { Icon: ShieldCheck, color: '#da291c' }, // firewall
  fortimanager: { Icon: Network, color: '#e4572e' }, // device manager
  fortianalyzer: { Icon: BarChart3, color: '#b1281f' }, // analytics/logging
  fortiauthenticator: { Icon: Fingerprint, color: '#f26722' }, // identity / SAML IdP
  microsoft_dns: { Icon: Globe, color: '#0078d4' },
  microsoft_entra: { Icon: UserCheck, color: '#2563eb' }, // identity
};

export function connectorVisual(kind: string): ConnectorVisual {
  return CONNECTORS[kind] ?? { Icon: Plug, color: '#64748b' };
}

export interface CategoryVisual {
  label: string;
  color: string;
  tint: string;
  Brand: () => JSX.Element;
}

function MicrosoftMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" fill="#f25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7fba00" />
      <rect x="1" y="13" width="10" height="10" fill="#00a4ef" />
      <rect x="13" y="13" width="10" height="10" fill="#ffb900" />
    </svg>
  );
}

function FortinetMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 3.5h18V10a11 11 0 0 1-9 10.8A11 11 0 0 1 3 10V3.5Z" fill="#da291c" />
      <path d="M8 9h8M8 12.5h5" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

const CATEGORIES: Record<string, CategoryVisual> = {
  fortinet: { label: 'Fortinet', color: '#da291c', tint: 'rgba(218,41,28,0.07)', Brand: FortinetMark },
  microsoft: { label: 'Microsoft', color: '#0078d4', tint: 'rgba(0,120,212,0.07)', Brand: MicrosoftMark },
};

export function categoryVisual(category: string): CategoryVisual {
  return (
    CATEGORIES[category] ?? {
      label: category.charAt(0).toUpperCase() + category.slice(1),
      color: '#64748b',
      tint: 'rgba(100,116,139,0.07)',
      Brand: () => <Plug size={16} className="text-slate-500" />,
    }
  );
}
