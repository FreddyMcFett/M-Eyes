import { ReactNode } from 'react';

interface Props {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  accent?: boolean;
}

export default function StatCard({ label, value, icon, accent }: Props) {
  return (
    <div className="f-card px-4 py-3 flex items-center gap-3">
      {icon && <div className={accent ? 'text-accent' : 'text-muted'}>{icon}</div>}
      <div>
        <div className="text-xl font-semibold leading-tight">{value}</div>
        <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      </div>
    </div>
  );
}
