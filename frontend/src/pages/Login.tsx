import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../api/client';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

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
    <div className="min-h-screen bg-sidebar flex items-center justify-center">
      <form onSubmit={submit} className="bg-topbar rounded shadow-2xl w-[360px] p-8">
        <div className="flex items-center justify-center gap-2 mb-6">
          <img src="/logo.svg" alt="M-Eyes" className="w-10 h-10 rounded" />
          <div>
            <div className="text-white font-bold text-xl tracking-wide">M-EYES</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest">DDI Platform</div>
          </div>
        </div>
        <label className="block text-slate-300 text-xs mb-1">Username</label>
        <input
          className="w-full mb-3 px-3 py-2 rounded bg-sidebar text-white border border-slate-600 focus:outline-none focus:border-accent text-sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <label className="block text-slate-300 text-xs mb-1">Password</label>
        <input
          type="password"
          className="w-full mb-4 px-3 py-2 rounded bg-sidebar text-white border border-slate-600 focus:outline-none focus:border-accent text-sm"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="text-danger text-xs mb-3">{error}</div>}
        <button
          type="submit"
          disabled={busy}
          className="w-full py-2 rounded bg-accent hover:bg-accent-dark text-white font-semibold text-sm disabled:opacity-50"
        >
          {busy ? 'Signing in…' : 'Login'}
        </button>
        <p className="text-slate-500 text-[11px] mt-4 text-center">Default credentials: admin / admin</p>
      </form>
    </div>
  );
}
