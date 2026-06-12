import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { getToken } from './api/client';
import AppShell from './components/AppShell';
import { ToastProvider } from './components/Toast';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Networks from './pages/ipam/Networks';
import NetworkDetail from './pages/ipam/NetworkDetail';
import Zones from './pages/dns/Zones';
import ZoneDetail from './pages/dns/ZoneDetail';
import Views from './pages/dns/Views';
import Subnets from './pages/dhcp/Subnets';
import SubnetDetail from './pages/dhcp/SubnetDetail';
import Leases from './pages/dhcp/Leases';
import Hosts from './pages/Hosts';
import Feeds from './pages/feeds/Feeds';
import Blocklist from './pages/feeds/Blocklist';
import DnsFirewall from './pages/feeds/DnsFirewall';
import ExtAttrs from './pages/ExtAttrs';
import Changelog from './pages/Changelog';
import Events from './pages/Events';
import Runbook from './pages/Runbook';
import Settings from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function RequireAuth({ children }: { children: JSX.Element }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="ipam" element={<Networks />} />
              <Route path="ipam/:id" element={<NetworkDetail />} />
              <Route path="dns" element={<Zones />} />
              <Route path="dns/:id" element={<ZoneDetail />} />
              <Route path="dns-views" element={<Views />} />
              <Route path="dhcp" element={<Subnets />} />
              <Route path="dhcp/:id" element={<SubnetDetail />} />
              <Route path="leases" element={<Leases />} />
              <Route path="hosts" element={<Hosts />} />
              <Route path="feeds" element={<Feeds />} />
              <Route path="blocklist" element={<Blocklist />} />
              <Route path="dnsfw" element={<DnsFirewall />} />
              <Route path="extattrs" element={<ExtAttrs />} />
              <Route path="changelog" element={<Changelog />} />
              <Route path="events" element={<Events />} />
              <Route path="runbook" element={<Runbook />} />
              <Route path="settings" element={<Settings />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
