import { createContext, useCallback, useContext, useState, ReactNode } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';

interface ToastItem {
  id: number;
  kind: 'success' | 'error';
  message: string;
}

const ToastContext = createContext<(kind: 'success' | 'error', message: string) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((kind: 'success' | 'error', message: string) => {
    const id = nextId++;
    setToasts((current) => [...current, { id, kind, message }]);
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-5 right-5 z-[100] space-y-2.5">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="flex items-center gap-2.5 pl-3 pr-4 py-3 rounded-xl text-table max-w-md text-white border backdrop-blur-xl"
            style={{
              animation: 'slide-in-right 0.32s cubic-bezier(0.22,1,0.36,1) both',
              background:
                toast.kind === 'success'
                  ? 'linear-gradient(180deg, rgba(16,23,42,0.92), rgba(10,17,32,0.92))'
                  : 'linear-gradient(180deg, rgba(40,16,22,0.92), rgba(28,10,14,0.92))',
              borderColor: toast.kind === 'success' ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.45)',
              boxShadow: '0 18px 40px -12px rgba(0,0,0,0.6)',
            }}
          >
            <span
              className="grid place-items-center w-7 h-7 rounded-lg shrink-0"
              style={{
                background: toast.kind === 'success' ? 'rgba(16,185,129,0.18)' : 'rgba(239,68,68,0.18)',
                color: toast.kind === 'success' ? 'var(--accent-soft)' : '#fca5a5',
              }}
            >
              {toast.kind === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            </span>
            <span className="text-slate-100">{toast.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
