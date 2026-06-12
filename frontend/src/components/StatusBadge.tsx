const STYLES: Record<string, string> = {
  used: 'bg-accent/15 text-accent-dark border-accent/40',
  reserved: 'bg-warning/15 text-amber-700 border-warning/40',
  dhcp: 'bg-info/15 text-sky-700 border-info/40',
  free: 'bg-slate-100 text-slate-500 border-slate-200',
  success: 'bg-accent/15 text-accent-dark border-accent/40',
  failed: 'bg-danger/15 text-red-700 border-danger/40',
  unreachable: 'bg-warning/15 text-amber-700 border-warning/40',
  create: 'bg-accent/15 text-accent-dark border-accent/40',
  update: 'bg-info/15 text-sky-700 border-info/40',
  delete: 'bg-danger/15 text-red-700 border-danger/40',
  rollback: 'bg-warning/15 text-amber-700 border-warning/40',
  info: 'bg-info/15 text-sky-700 border-info/40',
  warning: 'bg-warning/15 text-amber-700 border-warning/40',
  error: 'bg-danger/15 text-red-700 border-danger/40',
  debug: 'bg-slate-100 text-slate-500 border-slate-200',
  forward: 'bg-info/15 text-sky-700 border-info/40',
  reverse: 'bg-violet-100 text-violet-700 border-violet-200',
};

export default function StatusBadge({ value }: { value: string }) {
  const style = STYLES[value] ?? 'bg-slate-100 text-slate-600 border-slate-200';
  return (
    <span className={`inline-block px-2 py-0.5 rounded border text-xs font-medium ${style}`}>{value}</span>
  );
}
