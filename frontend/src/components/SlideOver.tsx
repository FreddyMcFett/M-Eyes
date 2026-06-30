import { ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export default function SlideOver({ title, open, onClose, children }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div
        className="absolute right-0 top-0 h-full w-[440px] max-w-[92vw] bg-white shadow-2xl flex flex-col border-l border-line"
        style={{ animation: 'slide-in-right 0.32s cubic-bezier(0.22,1,0.36,1) both' }}
      >
        <div className="flex items-center justify-between px-5 py-3.5 text-white app-topbar border-b border-[var(--shell-line)]">
          <h2 className="font-semibold text-sm tracking-tight">{title}</h2>
          <button
            onClick={onClose}
            className="grid place-items-center w-7 h-7 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X size={17} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  );
}
