import { useId } from 'react';

interface Props {
  percent: number;
  size?: number;
  label?: string;
}

export default function Donut({ percent, size = 78, label }: Props) {
  const uid = useId().replace(/[:]/g, '');
  const radius = size / 2 - 6;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(Math.max(percent, 0), 100);

  const stops =
    clamped > 90
      ? ['#fb7185', '#ef4444']
      : clamped > 70
        ? ['#fbbf24', '#f59e0b']
        : ['#34d399', '#06b6d4'];

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <defs>
            <linearGradient id={`dn-${uid}`} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor={stops[0]} />
              <stop offset="100%" stopColor={stops[1]} />
            </linearGradient>
          </defs>
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#dn-${uid})`}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - clamped / 100)}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 1s cubic-bezier(0.22,1,0.36,1)',
              filter: `drop-shadow(0 0 4px ${stops[1]}66)`,
            }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-sm font-bold text-ink tabular-nums">
          {clamped}%
        </div>
      </div>
      {label && <div className="text-xs text-muted mt-1.5 text-center max-w-[110px] truncate font-mono">{label}</div>}
    </div>
  );
}
