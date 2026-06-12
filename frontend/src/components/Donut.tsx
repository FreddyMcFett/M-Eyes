interface Props {
  percent: number;
  size?: number;
  label?: string;
}

export default function Donut({ percent, size = 72, label }: Props) {
  const radius = size / 2 - 6;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(Math.max(percent, 0), 100);
  const color = clamped > 90 ? 'var(--danger)' : clamped > 70 ? 'var(--warning)' : 'var(--accent)';
  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - clamped / 100)}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-table font-semibold">
          {clamped}%
        </div>
      </div>
      {label && <div className="text-xs text-muted mt-1 text-center max-w-[110px] truncate">{label}</div>}
    </div>
  );
}
