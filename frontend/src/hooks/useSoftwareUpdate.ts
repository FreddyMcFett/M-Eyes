import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { UpdateProgress, UpdateStatus } from '../api/types';

/**
 * Self-update lifecycle: check for a newer release, trigger an in-app update,
 * and follow its progress while the API restarts. Shared by the Settings page
 * and the Dashboard's inline update control so both behave identically.
 */
export function useSoftwareUpdate(enabled = true) {
  const qc = useQueryClient();
  const [updating, setUpdating] = useState(false);
  const [progress, setProgress] = useState<UpdateProgress | null>(null);
  const [done, setDone] = useState(false);
  const targetVersion = useRef<string | null>(null);

  const status = useQuery({
    queryKey: ['update-check'],
    queryFn: () => api.get<UpdateStatus>('/api/v1/system/update-check'),
    enabled,
    retry: 1,
  });

  // While an update runs the API restarts, so unreachable polls are expected
  // and shown as "restarting" rather than a failure. Completion is detected
  // when the restarted API reports the target version as its running version.
  useEffect(() => {
    if (!updating) return;
    let active = true;
    const poll = async () => {
      try {
        const s = await api.get<UpdateProgress>('/api/v1/system/update/status');
        if (!active) return;
        setProgress(s);
        if (s.phase === 'error') {
          setUpdating(false);
        } else if (targetVersion.current && s.current_version === targetVersion.current) {
          setUpdating(false);
          setDone(true);
        }
      } catch {
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

  const check = useMutation({
    mutationFn: () => api.get<UpdateStatus>('/api/v1/system/update-check?force=true'),
    onSuccess: (s) => qc.setQueryData(['update-check'], s),
  });

  const trigger = useMutation({
    mutationFn: () => api.post<UpdateProgress>('/api/v1/system/update'),
    onSuccess: (s) => {
      targetVersion.current = s.target_version;
      setProgress(s);
      setDone(false);
      setUpdating(true);
    },
  });

  return {
    status: status.data,
    checking: check.isPending || status.isFetching,
    checkError: status.isError,
    check: () => check.mutate(),
    trigger: () => trigger.mutate(),
    triggering: trigger.isPending,
    updating,
    progress,
    done,
    targetVersion: targetVersion.current,
  };
}
