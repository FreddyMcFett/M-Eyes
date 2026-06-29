import { ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}

export default function Modal({ title, open, onClose, children, wide }: Props) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div
        className={`relative bg-white rounded-2xl shadow-2xl max-h-[85vh] flex flex-col overflow-hidden border border-line animate-pop-in ${
          wide ? 'w-[780px]' : 'w-[480px]'
        }`}
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
