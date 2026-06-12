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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div
        className={`relative bg-white rounded shadow-2xl max-h-[85vh] flex flex-col ${
          wide ? 'w-[780px]' : 'w-[480px]'
        }`}
      >
        <div className="flex items-center justify-between px-4 py-3 bg-sidebar text-white rounded-t">
          <h2 className="font-semibold text-sm">{title}</h2>
          <button onClick={onClose} className="hover:text-accent" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
      </div>
    </div>
  );
}
