import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { EngineStatus } from '../api/types';

/* --------------------------------------------------------------------------
   useEngineSync — treats DNS (BIND) and DHCP (Kea) as native, always-on
   services rather than something the operator has to "deploy".

   Whenever the stored configuration version moves ahead of what an engine has
   applied, the change is pushed to that engine automatically in the background
   — once per version, so there is never a stampede and the user never has to
   click a "Deploy" button. The returned per-engine view exposes a calm service
   state (live / applying / pending / attention) for the UI to render.
   -------------------------------------------------------------------------- */

export type EngineTarget = 'bind' | 'kea';
export type EngineState = 'live' | 'applying' | 'pending' | 'attention' | 'idle';

const LABEL: Record<EngineTarget, string> = { bind: 'DNS', kea: 'DHCP' };
const TARGETS = Object.keys(LABEL) as EngineTarget[];

// Module-level guards shared by every hook instance (the header pills and any
// page badges) so a config bump fires a single background apply per version.
const attempted = new Set<string>();
const inflight = new Set<string>();

export interface EngineView {
  target: EngineTarget;
  label: string;
  state: EngineState;
  deployedVersion: number | null;
  configVersion: number;
  lastStatus: string | null;
  lastMessage: string | null;
}

export interface EngineSync {
  bind: EngineView;
  kea: EngineView;
  /** Force a re-apply now (manual override; bypasses the once-per-version guard). */
  reapply: (target: EngineTarget) => void;
}

export function useEngineSync(): EngineSync {
  const qc = useQueryClient();

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

  const configVersion = info?.config_version ?? 0;

  const fire = (target: EngineTarget, version: number, manual: boolean) => {
    const key = `${target}:${version}`;
    if (inflight.has(key)) return;
    if (!manual && attempted.has(key)) return;
    attempted.add(key);
    inflight.add(key);
    api
      .post(`/api/v1/deploy/${target}`)
      .catch(() => undefined) // failures surface through engine-status, not a toast
      .finally(() => {
        inflight.delete(key);
        qc.invalidateQueries({ queryKey: ['engine-status'] });
        qc.invalidateQueries({ queryKey: ['system-info'] });
      });
  };

  // True when there are committed config changes an engine has not yet attempted.
  const drift = (deployed: number | null) =>
    deployed === null ? configVersion > 0 : configVersion > deployed;

  useEffect(() => {
    if (!engines || !info) return;
    TARGETS.forEach((t) => {
      if (drift(engines[t].deployed_version)) fire(t, configVersion, false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [engines, info, configVersion]);

  const view = (target: EngineTarget): EngineView => {
    const engine = engines?.[target];
    const deployed = engine?.deployed_version ?? null;
    const lastStatus = engine?.last_status ?? null;
    const applying = inflight.has(`${target}:${configVersion}`) || drift(deployed);

    let state: EngineState;
    if (applying) state = 'applying';
    else if (lastStatus === 'failed') state = 'attention';
    else if (lastStatus === 'unreachable') state = 'pending';
    else if (lastStatus === 'success') state = 'live';
    else state = 'idle';

    return {
      target,
      label: LABEL[target],
      state,
      deployedVersion: deployed,
      configVersion,
      lastStatus,
      lastMessage: engine?.last_message ?? null,
    };
  };

  return {
    bind: view('bind'),
    kea: view('kea'),
    reapply: (t) => fire(t, configVersion, true),
  };
}
