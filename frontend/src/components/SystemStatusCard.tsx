import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  DownloadCloud,
  Loader2,
  RefreshCw,
  Server,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { SystemStatus } from '../api/types';
import { useSoftwareUpdate } from '../hooks/useSoftwareUpdate';
import { useClock } from '../hooks/useClock';
import { clockInZone, formatDuration } from '../lib/format';
import ConfirmDialog from './ConfirmDialog';

const PHASE_LABEL: Record<string, string> = {
  requested: 'Queued …',
  pulling: 'Downloading new version …',
  recreating: 'Restarting services …',
  done: 'Finishing up …',
  error: 'Update failed',
};

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-line last:border-0">
      <span className="text-muted text-xs">{label}</span>
      <span className={`text-table ${mono ? 'font-mono' : ''} text-right`}>{value}</span>
    </div>
  );
}

/** System status + inline software-update control for the operational dashboard. */
export default function SystemStatusCard({ status }: { status?: SystemStatus }) {
  const now = useClock(1000);
  const upd = useSoftwareUpdate(true);
  const [confirm, setConfirm] = useState(false);

  const tz = status?.timezone ?? 'UTC';
  const clock = clockInZone(tz, now);
  const offset = status?.utc_offset ? `UTC${status.utc_offset.replace(/(\d{2})(\d{2})/, '$1:$2')}` : '';
  const latest = upd.status?.latest_version;
  const updateAvailable = upd.status?.update_available;
  const pendingImages = upd.status?.pending_images;
  const inApp = upd.status?.in_app_update ?? status?.in_app_update;

  return (
    <div className="f-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Server size={16} className="text-accent" /> System Status
        </h3>
        <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-accent/15 text-accent-dark border border-accent/40">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" /> Operational
        </span>
      </div>

      <Row label="Version" value={<span className="font-mono">v{status?.version ?? '…'}</span>} />
      <Row label="Config version" value={<span className="font-mono">v{status?.config_version ?? 0}</span>} />
      <Row
        label="Local time"
        value={
          <span className="inline-flex items-center gap-1.5">
            <Clock size={12} className="text-muted" />
            <span className="font-mono">{clock.time}</span>
            <span className="text-muted text-xs">{clock.zone}</span>
          </span>
        }
      />
      <Row
        label="Time zone"
        value={
          <Link to="/settings" className="text-info hover:underline" title="Change in Settings">
            {tz}{offset ? ` · ${offset}` : ''}
          </Link>
        }
      />
      <Row label="Uptime" value={formatDuration(status?.resources?.host_uptime_seconds ?? status?.resources?.process_uptime_seconds)} mono />
      <Row label="Host" value={status?.hostname ?? '—'} mono />
      <Row label="Platform" value={<span className="text-xs">{status?.platform ?? '—'}</span>} />
      <Row label="Python" value={status?.python_version ?? '—'} mono />

      {/* Software update --------------------------------------------------- */}
      <div className="mt-3 pt-3 border-t border-line">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-slate-600">Software Updates</span>
          <button
            className="f-btn-secondary !py-1 !px-2 text-xs"
            onClick={() => upd.check()}
            disabled={upd.checking || upd.updating}
          >
            <RefreshCw size={12} className={upd.checking ? 'animate-spin' : ''} /> Check now
          </button>
        </div>
        <Row label="Latest release" value={<span className="font-mono">{latest ? `v${latest}` : 'unknown'}</span>} />

        {upd.done ? (
          <div className="border border-accent rounded p-2.5 bg-accent/5 mt-2">
            <div className="font-medium text-table mb-1 flex items-center gap-1.5 text-accent">
              <CheckCircle2 size={14} /> Update complete — now on v{upd.progress?.current_version ?? upd.targetVersion}
            </div>
            <p className="text-xs text-muted flex items-center gap-1.5">
              <Loader2 size={12} className="animate-spin" /> Reloading the interface…{' '}
              <button className="text-info hover:underline" onClick={() => window.location.reload()}>
                Reload now
              </button>
            </p>
          </div>
        ) : upd.updating ? (
          <div className="border border-info rounded p-2.5 bg-info/5 mt-2">
            <div className="font-medium text-table mb-1 flex items-center gap-1.5">
              <Loader2 size={14} className="animate-spin text-info" />
              {PHASE_LABEL[upd.progress?.phase ?? 'requested'] ?? 'Updating …'}
            </div>
            <p className="text-xs text-muted">
              Updating to v{upd.targetVersion}. The interface reconnects automatically once the
              services restart; your data is preserved.
            </p>
          </div>
        ) : upd.progress?.phase === 'error' ? (
          <div className="border border-danger rounded p-2.5 bg-danger/5 mt-2">
            <div className="font-medium text-table flex items-center gap-1.5 text-danger">
              <AlertTriangle size={14} /> {upd.progress.message || 'Update failed'}
            </div>
          </div>
        ) : upd.checkError ? (
          <div className="text-xs text-warning mt-2 flex items-center gap-1.5">
            <AlertTriangle size={13} /> Couldn’t reach the update server.
          </div>
        ) : updateAvailable ? (
          <div className="border border-warning rounded p-2.5 bg-warning/5 mt-2">
            <div className="font-medium text-table mb-1.5">Update available — v{latest}</div>
            {inApp ? (
              <button className="f-btn-primary !py-1 text-xs" onClick={() => setConfirm(true)}>
                <DownloadCloud size={13} /> Update now & restart
              </button>
            ) : (
              <Link to="/settings" className="text-info text-xs hover:underline">Upgrade from Settings →</Link>
            )}
          </div>
        ) : pendingImages ? (
          <div className="text-xs text-info mt-2 flex items-center gap-1.5">
            <Loader2 size={13} className="animate-spin" /> v{latest} is publishing — images aren’t
            ready to download yet. Check again shortly.
          </div>
        ) : upd.status ? (
          <div className="mt-2">
            <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded bg-accent/15 text-accent-dark border border-accent/40">
              <CheckCircle2 size={12} /> Up to date
            </span>
          </div>
        ) : null}
      </div>

      <ConfirmDialog
        title="Update & restart M-Eyes"
        message={`Download v${latest} and restart the M-Eyes services now? The web interface will be briefly unavailable while it restarts. Your configuration is preserved and database migrations run automatically on start.`}
        open={confirm}
        onCancel={() => setConfirm(false)}
        onConfirm={() => {
          upd.trigger();
          setConfirm(false);
        }}
      />
    </div>
  );
}
