import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
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
import { EngineStatus } from '../api/types';
import GlobalSearch from './GlobalSearch';

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

function EngineDot({ status, label }: { status: string | null; label: string }) {
  const color =
    status === 'success' ? 'bg-accent' : status === 'failed' ? 'bg-danger' : status === 'unreachable' ? 'bg-warning' : 'bg-slate-500';
  return (
    <span className="flex items-center gap-1.5 text-xs text-slate-300" title={`${label}: ${status ?? 'never deployed'}`}>
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

export default function AppShell() {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const { data: info } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => api.get<{ version: string; config_version: number }>('/api/v1/system/info'),
    refetchInterval: 5000,
  });
  const { data: engines } = useQuery({
    queryKey: ['engine-status'],
    queryFn: () => api.get<EngineStatus>('/api/v1/deploy/status'),
    refetchInterval: 5000,
  });

  const logout = () => {
    clearToken();
    navigate('/login');
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 pl-8 pr-3 py-1.5 text-[13px] border-l-[3px] transition-colors ${
      isActive
        ? 'bg-sidebar-active border-accent text-white'
        : 'border-transparent text-slate-300 hover:bg-sidebar-hover hover:text-white'
    }`;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[230px] bg-sidebar flex flex-col shrink-0">
        <div className="flex items-center gap-2 px-4 py-3.5 bg-topbar">
          <img src="/logo.svg" alt="M-Eyes" className="w-7 h-7 rounded" />
          <div>
            <div className="text-white font-bold leading-tight tracking-wide">M-EYES</div>
            <div className="text-[10px] text-slate-400 uppercase">DDI Platform</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          <NavLink to="/" end className={linkClass}>
            <LayoutDashboard size={14} /> Dashboard
          </NavLink>
          {SECTIONS.map((section) => {
            const isCollapsed = collapsed[section.label];
            return (
              <div key={section.label}>
                <button
                  className="w-full flex items-center gap-2 px-4 py-2 mt-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200"
                  onClick={() => setCollapsed((c) => ({ ...c, [section.label]: !c[section.label] }))}
                >
                  {section.icon}
                  <span className="flex-1 text-left">{section.label}</span>
                  {isCollapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                </button>
                {!isCollapsed &&
                  section.items.map((item) => (
                    <NavLink key={item.to} to={item.to} className={linkClass}>
                      {item.icon} {item.label}
                    </NavLink>
                  ))}
              </div>
            );
          })}
          <div className="mt-2">
            <div className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
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
        <div className="px-4 py-2 text-[10px] text-slate-500 border-t border-slate-700">
          v{info?.version ?? '…'}
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-topbar flex items-center gap-4 px-4 py-2 shrink-0">
          <div className="text-slate-200 text-sm font-medium">M-Eyes Management</div>
          <span className="ml-2 px-2 py-0.5 rounded bg-sidebar-active text-accent text-xs font-mono">
            config v{info?.config_version ?? 0}
          </span>
          <div className="ml-auto flex items-center gap-4">
            <GlobalSearch />
            <EngineDot status={engines?.bind.last_status ?? null} label="BIND" />
            <EngineDot status={engines?.kea.last_status ?? null} label="Kea" />
            <NavLink
              to="/docs"
              className={({ isActive }) =>
                `flex items-center transition-colors ${isActive ? 'text-accent' : 'text-slate-300 hover:text-white'}`
              }
              title="Documentation"
            >
              <HelpCircle size={17} />
            </NavLink>
            <span className="flex items-center gap-1.5 text-xs text-slate-300">
              <User size={13} /> admin
            </span>
            <button onClick={logout} className="text-slate-300 hover:text-white" title="Log out">
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
