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
      {/* top accent line — brighter on the accent card */}
      <span
        className={`absolute inset-x-0 top-0 h-0.5 rounded-t-[14px] bg-gradient-to-r from-transparent to-transparent ${
          accent ? 'via-accent' : 'via-accent/40'
        }`}
      />
      {icon && (
        <div
          className={`grid place-items-center w-11 h-11 rounded-xl shrink-0 transition-transform duration-300 group-hover:scale-105 ${
            accent ? 'text-white' : 'text-accent-dark'
          }`}
          style={
            accent
              ? {
                  background: 'linear-gradient(150deg, var(--accent-soft), var(--accent))',
                  boxShadow: '0 8px 20px -8px rgba(16,185,129,0.6)',
                }
              : { background: 'linear-gradient(150deg, rgba(16,185,129,0.14), rgba(6,182,212,0.10))' }
          }
        >
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <div className="text-2xl font-bold leading-tight tracking-tight text-ink tabular-nums">{value}</div>
        <div className="text-[11px] text-muted uppercase tracking-wider font-semibold mt-0.5 truncate">{label}</div>
      </div>
    </>
  );

  const base = 'group relative overflow-hidden f-card px-4 py-3.5 flex items-center gap-3.5';

  if (to) {
    return (
      <Link
        to={to}
        title={`Open ${label}`}
        className={`${base} hover-lift hover:border-accent/50 focus:outline-none focus:ring-2 focus:ring-accent/30 cursor-pointer`}
      >
        {body}
      </Link>
    );
  }

  return <div className={base}>{body}</div>;
}
