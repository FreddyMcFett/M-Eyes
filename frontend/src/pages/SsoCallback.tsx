import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../api/client';

export default function SsoCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      setToken(token);
      // Strip the token from the URL before entering the app.
      navigate('/', { replace: true });
    } else {
      navigate('/login?sso_error=1', { replace: true });
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-sidebar flex items-center justify-center text-slate-300 text-sm">
      Completing single sign-on…
    </div>
  );
}
