import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface Props {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  accent?: boolean;
  /** When set, the card becomes a clickable link to this route. */
  to?: string;
}

export default function StatCard({ label, value, icon, accent, to }: Props) {
  const body = (
    <>
      {icon && <div className={accent ? 'text-accent' : 'text-muted'}>{icon}</div>}
      <div>
        <div className="text-xl font-semibold leading-tight">{value}</div>
        <div className="text-xs text-muted uppercase tracking-wide">{label}</div>
      </div>
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        title={`Open ${label}`}
        className="f-card px-4 py-3 flex items-center gap-3 transition-colors hover:border-accent hover:shadow-md focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
      >
        {body}
      </Link>
    );
  }

  return <div className="f-card px-4 py-3 flex items-center gap-3">{body}</div>;
}
