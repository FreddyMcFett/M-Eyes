import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, Lock, User } from 'lucide-react';
import { api, setToken } from '../api/client';
import { SsoStatus } from '../api/types';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [sso, setSso] = useState<SsoStatus | null>(null);

  useEffect(() => {
    api.get<SsoStatus>('/api/v1/sso/status').then(setSso).catch(() => setSso(null));
    if (new URLSearchParams(window.location.search).get('sso_error')) {
      setError('Single sign-on failed. Please try again or use local credentials.');
    }
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api.post<{ access_token: string }>('/api/v1/auth/login', {
        username,
        password,
      });
      setToken(result.access_token);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-shell">
      {/* Animated deep-space backdrop ------------------------------------- */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(900px 600px at 15% 10%, rgba(16,185,129,0.18), transparent 55%),' +
              'radial-gradient(820px 560px at 85% 20%, rgba(99,102,241,0.18), transparent 55%),' +
              'radial-gradient(760px 620px at 50% 110%, rgba(6,182,212,0.16), transparent 55%),' +
              'linear-gradient(180deg, #0a1120 0%, #0d1526 60%, #0a1120 100%)',
          }}
        />
        <div className="absolute inset-0 bg-grid-faint [background-size:42px_42px] opacity-[0.5] [mask-image:radial-gradient(60%_60%_at_50%_40%,#000,transparent)]" />
        <div className="absolute top-[12%] left-[18%] h-72 w-72 rounded-full bg-accent/25 blur-3xl animate-[drift_22s_ease-in-out_infinite]" />
        <div className="absolute bottom-[10%] right-[16%] h-80 w-80 rounded-full bg-brand-violet/25 blur-3xl animate-[drift_26s_ease-in-out_infinite_reverse]" />
        <div className="absolute top-[40%] right-[30%] h-56 w-56 rounded-full bg-brand-cyan/20 blur-3xl animate-[drift_19s_ease-in-out_infinite]" />
      </div>

      {/* Card -------------------------------------------------------------- */}
      <form
        onSubmit={submit}
        className="relative w-[380px] rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl p-8 shadow-2xl animate-fade-up"
        style={{ boxShadow: '0 30px 80px -20px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.08)' }}
      >
        <div className="flex flex-col items-center text-center mb-7">
          <div className="relative mb-3">
            <div className="absolute inset-0 rounded-2xl bg-accent/50 blur-xl animate-pulse" />
            <img src="/logo.svg" alt="M-Eyes" className="relative w-14 h-14 rounded-2xl ring-1 ring-white/20" />
          </div>
          <div className="text-2xl font-extrabold tracking-[0.16em] text-gradient">M-EYES</div>
          <div className="text-[10px] text-slate-400 uppercase tracking-[0.3em] mt-1">DDI Control Plane</div>
        </div>

        <label className="block text-slate-400 text-[11px] font-semibold uppercase tracking-wider mb-1.5">
          Username
        </label>
        <div className="relative mb-4">
          <User size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white/5 text-white border border-white/10 placeholder-slate-500 focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/30 text-sm transition-all"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="admin"
            autoFocus
          />
        </div>

        <label className="block text-slate-400 text-[11px] font-semibold uppercase tracking-wider mb-1.5">
          Password
        </label>
        <div className="relative mb-5">
          <Lock size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="password"
            className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-white/5 text-white border border-white/10 placeholder-slate-500 focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/30 text-sm transition-all"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-danger text-xs animate-fade-in">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="group w-full py-2.5 rounded-xl text-white font-semibold text-sm disabled:opacity-50 transition-all hover:-translate-y-0.5"
          style={{
            background: 'linear-gradient(180deg, var(--accent-soft), var(--accent))',
            boxShadow: '0 14px 30px -10px rgba(16,185,129,0.6), inset 0 1px 0 rgba(255,255,255,0.25)',
          }}
        >
          <span className="inline-flex items-center justify-center gap-2">
            {busy ? (
              <>
                <Loader2 size={15} className="animate-spin" /> Signing in…
              </>
            ) : (
              <>
                Sign in
                <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
              </>
            )}
          </span>
        </button>

        {sso?.enabled && (
          <>
            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px bg-white/10" />
              <span className="text-slate-500 text-[10px] uppercase tracking-[0.2em]">or</span>
              <div className="flex-1 h-px bg-white/10" />
            </div>
            <a
              href={sso.login_url}
              className="block w-full py-2.5 rounded-xl border border-accent/50 text-accent-soft hover:bg-accent/15 hover:text-white font-semibold text-sm text-center transition-all"
            >
              {sso.button_label}
            </a>
          </>
        )}
      </form>
    </div>
  );
}
