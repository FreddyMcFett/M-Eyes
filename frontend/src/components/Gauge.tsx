interface Props {
  /** 0–100 (null renders an "n/a" gauge). */
  percent: number | null;
  label: string;
  /** Big centre readout; defaults to "<percent>%". */
  readout?: string;
  /** Small line under the readout. */
  sub?: string;
  size?: number;
}

/**
 * Neon circular gauge for the Command Center. Pure SVG so it needs no charting
 * dependency; the arc colour shifts green → amber → red as it fills.
 */
export default function Gauge({ percent, label, readout, sub, size = 116 }: Props) {
  const value = percent === null || !Number.isFinite(percent) ? 0 : Math.min(100, Math.max(0, percent));
  const stroke = 9;
  const radius = size / 2 - stroke;
  const circumference = 2 * Math.PI * radius;
  // Leave a 25% gap at the bottom for an open "speedometer" look.
  const arc = 0.75;
  const dash = circumference * arc;
  const color = value > 90 ? '#f87171' : value > 75 ? '#fbbf24' : '#4ade80';
  const center = size / 2;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="block" style={{ transform: 'rotate(135deg)' }}>
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(56,189,248,0.14)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
          />
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${dash * (value / 100)} ${circumference}`}
            style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dasharray 0.7s cubic-bezier(0.22,1,0.36,1), stroke 0.4s' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-xl font-bold cc-glow" style={{ color }}>
            {readout ?? (percent === null ? 'n/a' : `${Math.round(value)}%`)}
          </div>
          {sub && <div className="text-[10px] mt-0.5" style={{ color: 'var(--cc-muted)' }}>{sub}</div>}
        </div>
      </div>
      <div className="mt-1 text-[11px] tracking-wider uppercase" style={{ color: 'var(--cc-muted)' }}>{label}</div>
    </div>
  );
}
