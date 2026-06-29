import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Boxes,
  ChevronDown,
  ChevronRight,
  Cpu,
  FileText,
  Globe,
  HelpCircle,
  History,
  KeyRound,
  LayoutDashboard,
  LayoutGrid,
  Layers,
  List,
  ListChecks,
  LogOut,
  Network as NetworkIcon,
  Plug,
  Rss,
  Server,
  Settings as SettingsIcon,
  Shield,
  ShieldBan,
  ShieldOff,
  Tags,
  User,
  Users as UsersIcon,
} from 'lucide-react';
import { api, clearToken } from '../api/client';
import GlobalSearch from './GlobalSearch';
import { EngineStatusPills } from './EngineStatus';

interface NavItem {
  to: string;
  label: string;
  icon: JSX.Element;
}

interface NavSection {
  label: string;
  icon: JSX.Element;
  items: NavItem[];
}

const SECTIONS: NavSection[] = [
  {
    label: 'Network',
    icon: <NetworkIcon size={15} />,
    items: [
      { to: '/ipam', label: 'IPAM', icon: <List size={14} /> },
      { to: '/dns', label: 'DNS', icon: <Globe size={14} /> },
      { to: '/dns-views', label: 'DNS Views', icon: <Layers size={14} /> },
      { to: '/dhcp', label: 'DHCP', icon: <Server size={14} /> },
      { to: '/leases', label: 'Leases', icon: <ListChecks size={14} /> },
      { to: '/hosts', label: 'Hosts', icon: <Activity size={14} /> },
      { to: '/assets', label: 'Assets', icon: <Boxes size={14} /> },
    ],
  },
  {
    label: 'Security Fabric',
    icon: <Shield size={15} />,
    items: [
      { to: '/feeds', label: 'Fortinet Feeds', icon: <Rss size={14} /> },
      { to: '/blocklist', label: 'Blocklist', icon: <ShieldBan size={14} /> },
      { to: '/dnsfw', label: 'DNS Firewall', icon: <ShieldOff size={14} /> },
    ],
  },
  {
    label: 'Enterprise',
    icon: <Plug size={15} />,
    items: [
      { to: '/integrations', label: 'Integrations', icon: <Plug size={14} /> },
      { to: '/automation', label: 'Automation', icon: <Cpu size={14} /> },
    ],
  },
  {
    label: 'Log & Report',
    icon: <FileText size={15} />,
    items: [
      { to: '/changelog', label: 'Change Log', icon: <History size={14} /> },
      { to: '/events', label: 'Events', icon: <Activity size={14} /> },
      { to: '/runbook', label: 'Runbook', icon: <FileText size={14} /> },
    ],
  },
];

export default function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  // The Command Center is a full-bleed dark cockpit: it fills the content area
  // edge to edge and continues straight from the top bar, so it skips the light
  // padding the operational pages use (which would otherwise frame it in a grey
  // gutter). Other routes keep the standard FortiOS light canvas with padding.
  const cockpit = location.pathname === '/';

  const { data: info } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => api.get<{ version: string; config_version: number }>('/api/v1/system/info'),
    refetchInterval: 5000,
  });

  const logout = () => {
    clearToken();
    navigate('/login');
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `group relative flex items-center gap-2.5 pl-8 pr-3 py-2 text-[13px] border-l-[3px] transition-all duration-200 [&>svg]:transition-colors ${
      isActive
        ? 'border-accent text-white bg-[linear-gradient(90deg,rgba(16,185,129,0.20),rgba(16,185,129,0.015))] shadow-[inset_0_0_22px_-8px_rgba(16,185,129,0.6)] [&>svg]:text-accent-soft'
        : 'border-transparent text-slate-300/85 hover:text-white hover:bg-white/[0.06] [&>svg]:text-slate-400 hover:[&>svg]:text-slate-200'
    }`;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar — deep-space glass rail */}
      <aside className="app-sidebar relative w-[238px] flex flex-col shrink-0">
        {/* ambient top glow */}
        <div className="pointer-events-none absolute -top-16 -left-10 h-48 w-48 rounded-full bg-accent/20 blur-3xl" />
        <div className="pointer-events-none absolute top-24 -right-16 h-48 w-48 rounded-full bg-brand-indigo/20 blur-3xl" />

        <div className="relative flex items-center gap-2.5 px-4 py-4 border-b border-[var(--shell-line)]">
          <div className="relative shrink-0">
            <div className="absolute inset-0 rounded-xl bg-accent/40 blur-md" />
            <img src="/logo.svg" alt="M-Eyes" className="relative w-8 h-8 rounded-xl ring-1 ring-white/15" />
          </div>
          <div className="leading-tight">
            <div className="font-extrabold tracking-[0.14em] text-gradient text-[15px]">M-EYES</div>
            <div className="text-[9.5px] text-slate-400 uppercase tracking-[0.22em]">DDI Platform</div>
          </div>
        </div>

        <nav className="relative flex-1 overflow-y-auto py-3">
          <NavLink to="/" end className={linkClass}>
            <LayoutGrid size={15} /> Command Center
          </NavLink>
          <NavLink to="/dashboard" className={linkClass}>
            <LayoutDashboard size={15} /> Dashboard
          </NavLink>
          {SECTIONS.map((section) => {
            const isCollapsed = collapsed[section.label];
            return (
              <div key={section.label} className="mt-3">
                <button
                  className="w-full flex items-center gap-2 px-4 py-1.5 text-[10.5px] font-bold uppercase tracking-[0.16em] text-slate-500 hover:text-slate-300 transition-colors"
                  onClick={() => setCollapsed((c) => ({ ...c, [section.label]: !c[section.label] }))}
                >
                  <span className="text-slate-500">{section.icon}</span>
                  <span className="flex-1 text-left">{section.label}</span>
                  {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                </button>
                <div
                  className={`overflow-hidden transition-all duration-300 ${
                    isCollapsed ? 'max-h-0 opacity-0' : 'max-h-[420px] opacity-100'
                  }`}
                >
                  {section.items.map((item) => (
                    <NavLink key={item.to} to={item.to} className={linkClass}>
                      {item.icon} {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
          <div className="mt-3">
            <div className="px-4 py-1.5 text-[10.5px] font-bold uppercase tracking-[0.16em] text-slate-500 flex items-center gap-2">
              <SettingsIcon size={15} /> System
            </div>
            <NavLink to="/extattrs" className={linkClass}>
              <Tags size={14} /> Extensible Attrs
            </NavLink>
            <NavLink to="/users" className={linkClass}>
              <UsersIcon size={14} /> Users &amp; Roles
            </NavLink>
            <NavLink to="/sso" className={linkClass}>
              <KeyRound size={14} /> SSO / SAML
            </NavLink>
            <NavLink to="/settings" className={linkClass}>
              <SettingsIcon size={14} /> Settings
            </NavLink>
          </div>
        </nav>
        <div className="relative px-4 py-2.5 text-[10px] text-slate-500 border-t border-[var(--shell-line)] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_6px] shadow-accent animate-pulse" />
          M-Eyes v{info?.version ?? '…'}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="app-topbar relative z-20 flex items-center gap-4 px-5 py-2.5 shrink-0">
          <div className="text-slate-200 text-sm font-semibold tracking-tight">M-Eyes Management</div>
          <span className="ml-1 inline-flex items-center px-2.5 py-1 rounded-lg bg-accent/15 text-accent-soft text-[11px] font-mono border border-accent/25">
            config v{info?.config_version ?? 0}
          </span>
          <div className="ml-auto flex items-center gap-4">
            <GlobalSearch />
            <EngineStatusPills />
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-slate-400 hover:text-white transition-colors"
              title="Documentation (opens in a new tab)"
            >
              <HelpCircle size={17} />
            </a>
            <span className="flex items-center gap-1.5 text-xs text-slate-300 pl-3 border-l border-[var(--shell-line)]">
              <span className="grid place-items-center w-6 h-6 rounded-lg bg-white/10 text-slate-200">
                <User size={13} />
              </span>
              admin
            </span>
            <button onClick={logout} className="text-slate-400 hover:text-danger transition-colors" title="Log out">
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <main className={`flex-1 overflow-y-auto ${cockpit ? 'bg-[#05070f]' : 'p-5'}`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
