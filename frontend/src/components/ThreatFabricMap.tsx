import { useId } from 'react';
import { formatCompact } from '../lib/format';
import { prefersReducedMotion, useCountUp } from '../hooks/useCountUp';

/* --------------------------------------------------------------------------
   ThreatFabricMap — the signature "exposure map" of the Command Center.

   A single responsive SVG that draws the security fabric as a flow graph:
   intel sources on the left fan in through glowing bezier conduits to an
   animated concentric-ring core (the headline KPIs), then fan back out to two
   outcome branches (active signals / enforced defenses) on the right. Every
   number counts up; the conduits pulse with travelling dashes; the core rings
   rotate and a radar sweep orbits the centre. All motion collapses under
   `prefers-reduced-motion`.

   Everything lives in one SVG view-box so the conduits always meet their nodes
   precisely, at any width.
   -------------------------------------------------------------------------- */

export interface FabricSource {
  id: string;
  name: string;
  value: number;
  color: string;
}
export interface FabricMetric {
  id: string;
  value: number;
  label: string;
  color: string;
}
export interface FabricCard {
  id: string;
  value: number;
  label: string;
  color: string;
}
export interface FabricBranch {
  id: string;
  label: string;
  total: number;
  color: string;
  cards: FabricCard[];
}

interface Props {
  sources: FabricSource[];
  metrics: FabricMetric[];
  active: FabricBranch;
  resolved: FabricBranch;
}

/* Fixed view-box geometry — the whole map is laid out in these coordinates. */
const VW = 1200;
const VH = 470;
const CX = 545;
const CY = 235;
const R = 118; // core connection radius
const SRC_X = 300; // x of the left source node dots
const HX = 795; // x of the right branch hubs
const HUB_R = 18;
const AY = 165; // active hub y
const RY = 330; // resolved hub y
const CARD_X = 905;
const CARD_W = 282;
const CARD_H = 58;
const ACTIVE_CARD_Y = [112, 206];
const RESOLVED_CARD_Y = [300, 392];

/** Smooth horizontal S-curve between two points (control points pushed inward). */
function hCurve(x1: number, y1: number, x2: number, y2: number, k = 0.5): string {
  const mx = x1 + (x2 - x1) * k;
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
}

/** SVG <text> whose numeric content counts up to `value` and renders compact. */
function NumText({
  value,
  ...rest
}: { value: number } & React.SVGProps<SVGTextElement>) {
  const v = useCountUp(value);
  return <text {...rest}>{formatCompact(v)}</text>;
}

/** A travelling dash conduit; the dash offset animates so it appears to flow. */
function Conduit({
  d,
  stroke,
  motion,
  reverse,
  dur = 2.4,
}: {
  d: string;
  stroke: string;
  motion: boolean;
  reverse?: boolean;
  dur?: number;
}) {
  return (
    <g>
      {/* faint full-strength base line */}
      <path d={d} fill="none" stroke={stroke} strokeOpacity={0.18} strokeWidth={1.6} />
      {/* travelling energy dashes */}
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeDasharray="2 12"
        style={{ filter: 'url(#fm-glow)' }}
      >
        {motion && (
          <animate
            attributeName="stroke-dashoffset"
            from={reverse ? '0' : '28'}
            to={reverse ? '28' : '0'}
            dur={`${dur}s`}
            repeatCount="indefinite"
          />
        )}
      </path>
    </g>
  );
}

export default function ThreatFabricMap({ sources, metrics, active, resolved }: Props) {
  const uid = useId().replace(/[:]/g, '');
  const motion = !prefersReducedMotion();

  const src = sources.slice(0, 6);
  const top = 60;
  const bottom = 412;
  const srcY = (i: number) => (src.length === 1 ? CY : top + ((bottom - top) * (i + 0.5)) / src.length);

  const mx = metrics.slice(0, 3);
  const metricX = mx.length === 1 ? [CX] : mx.length === 2 ? [CX - 90, CX + 90] : [CX - 138, CX, CX + 138];

  const cardRows = (branch: FabricBranch, ys: number[]) => branch.cards.slice(0, ys.length);

  return (
    <div className="cc-map">
      <svg viewBox={`0 0 ${VW} ${VH}`} className="cc-map-svg" role="img" aria-label="Security fabric exposure map">
        <defs>
          <linearGradient id={`fm-left-${uid}`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--cc-teal)" />
            <stop offset="100%" stopColor="var(--cc-cyan)" />
          </linearGradient>
          <radialGradient id={`fm-core-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(34,211,238,0.30)" />
            <stop offset="45%" stopColor="rgba(45,212,191,0.10)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <filter id="fm-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Core ambient glow */}
        <circle cx={CX} cy={CY} r={165} fill={`url(#fm-core-${uid})`} />

        {/* ---- Conduits (drawn first, under the nodes) -------------------- */}
        {src.map((s, i) => (
          <Conduit key={`cl-${s.id}`} d={hCurve(SRC_X, srcY(i), CX - R, CY)} stroke={s.color} motion={motion} dur={2 + (i % 4) * 0.35} />
        ))}
        {/* core → branch hubs */}
        <Conduit d={hCurve(CX + R, CY, HX - HUB_R, AY)} stroke={active.color} motion={motion} reverse dur={2.2} />
        <Conduit d={hCurve(CX + R, CY, HX - HUB_R, RY)} stroke={resolved.color} motion={motion} reverse dur={2.6} />
        {/* hubs → cards */}
        {cardRows(active, ACTIVE_CARD_Y).map((c, i) => (
          <Conduit key={`al-${c.id}`} d={hCurve(HX + HUB_R, AY, CARD_X, ACTIVE_CARD_Y[i])} stroke={c.color} motion={motion} reverse dur={2 + i * 0.4} />
        ))}
        {cardRows(resolved, RESOLVED_CARD_Y).map((c, i) => (
          <Conduit key={`rl-${c.id}`} d={hCurve(HX + HUB_R, RY, CARD_X, RESOLVED_CARD_Y[i])} stroke={c.color} motion={motion} reverse dur={2.2 + i * 0.4} />
        ))}

        {/* ---- Left source nodes ----------------------------------------- */}
        {src.map((s, i) => {
          const y = srcY(i);
          const name = s.name.length > 17 ? `${s.name.slice(0, 16)}…` : s.name;
          return (
            <g key={`sn-${s.id}`}>
              <rect x={118} y={y - 7} width={14} height={14} rx={3} fill="none" stroke={s.color} strokeWidth={1.4} strokeOpacity={0.8} />
              <circle cx={125} cy={y} r={2} fill={s.color} />
              <text x={144} y={y + 4} className="cc-map-src-name">
                {name}
              </text>
              <NumText value={s.value} x={290} y={y + 4} textAnchor="end" className="cc-map-src-val" style={{ fill: s.color }} />
              <circle cx={SRC_X} cy={y} r={5} fill={s.color} style={{ filter: 'url(#fm-glow)' }} />
              {motion && <circle cx={SRC_X} cy={y} r={5} fill="none" stroke={s.color} strokeWidth={1}>
                <animate attributeName="r" from="5" to="13" dur="2.4s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.7" to="0" dur="2.4s" repeatCount="indefinite" />
              </circle>}
            </g>
          );
        })}

        {/* ---- Core rings ------------------------------------------------- */}
        <g style={{ filter: 'url(#fm-glow)' }}>
          <circle cx={CX} cy={CY} r={R} fill="none" stroke="var(--cc-cyan)" strokeOpacity={0.22} strokeWidth={1} />
          <circle cx={CX} cy={CY} r={70} fill="none" stroke="var(--cc-teal)" strokeOpacity={0.28} strokeWidth={1} />
          {/* rotating dashed ring */}
          <g>
            {motion && (
              <animateTransform attributeName="transform" type="rotate" from={`0 ${CX} ${CY}`} to={`360 ${CX} ${CY}`} dur="48s" repeatCount="indefinite" />
            )}
            <circle cx={CX} cy={CY} r={104} fill="none" stroke="var(--cc-cyan)" strokeOpacity={0.55} strokeWidth={1.4} strokeDasharray="2 8" />
          </g>
          {/* counter-rotating fine ring */}
          <g>
            {motion && (
              <animateTransform attributeName="transform" type="rotate" from={`360 ${CX} ${CY}`} to={`0 ${CX} ${CY}`} dur="70s" repeatCount="indefinite" />
            )}
            <circle cx={CX} cy={CY} r={88} fill="none" stroke="var(--cc-violet)" strokeOpacity={0.45} strokeWidth={1} strokeDasharray="1 11" />
          </g>
          {/* radar sweep */}
          <g>
            {motion && (
              <animateTransform attributeName="transform" type="rotate" from={`0 ${CX} ${CY}`} to={`360 ${CX} ${CY}`} dur="6s" repeatCount="indefinite" />
            )}
            <path d={`M ${CX} ${CY} L ${CX + 104} ${CY - 26} A 104 104 0 0 1 ${CX + 104} ${CY + 4} Z`} fill="var(--cc-cyan)" fillOpacity={0.12} />
            <line x1={CX} y1={CY} x2={CX + 104} y2={CY} stroke="var(--cc-cyan)" strokeOpacity={0.6} strokeWidth={1.4} />
          </g>
          {/* orbiting comet dots */}
          {motion &&
            [
              { r: 104, dur: 11, c: 'var(--cc-cyan)' },
              { r: 88, dur: 8, c: 'var(--cc-violet)' },
              { r: 70, dur: 14, c: 'var(--cc-teal)' },
            ].map((o, i) => (
              <g key={`orb-${i}`}>
                <animateTransform attributeName="transform" type="rotate" from={`${i * 120} ${CX} ${CY}`} to={`${360 + i * 120} ${CX} ${CY}`} dur={`${o.dur}s`} repeatCount="indefinite" />
                <circle cx={CX + o.r} cy={CY} r={2.6} fill={o.c} />
              </g>
            ))}
        </g>

        {/* ---- Core headline numbers ------------------------------------- */}
        {mx.map((m, i) => {
          const gx = metricX[i];
          const lines = m.label.split(' ');
          return (
            <g key={`mt-${m.id}`}>
              <NumText value={m.value} x={gx} y={CY - 2} textAnchor="middle" className="cc-map-core-val" style={{ fill: m.color }} />
              <text x={gx} y={CY + 17} textAnchor="middle" className="cc-map-core-lbl">
                {lines[0]}
              </text>
              {lines[1] && (
                <text x={gx} y={CY + 28} textAnchor="middle" className="cc-map-core-lbl">
                  {lines.slice(1).join(' ')}
                </text>
              )}
            </g>
          );
        })}

        {/* ---- Right branch hubs + labels -------------------------------- */}
        {[
          { branch: active, hy: AY, lblY: AY - 33, ys: ACTIVE_CARD_Y },
          { branch: resolved, hy: RY, lblY: RY + 38, ys: RESOLVED_CARD_Y },
        ].map(({ branch, hy, lblY, ys }) => (
          <g key={`hub-${branch.id}`}>
            <circle cx={HX} cy={hy} r={HUB_R + 5} fill="none" stroke={branch.color} strokeOpacity={0.25} strokeWidth={1} />
            <circle cx={HX} cy={hy} r={HUB_R} fill="rgba(8,15,30,0.85)" stroke={branch.color} strokeWidth={1.6} style={{ filter: 'url(#fm-glow)' }} />
            <NumText value={branch.total} x={HX} y={hy + 4} textAnchor="middle" className="cc-map-hub-val" style={{ fill: branch.color }} />
            {motion && (
              <circle cx={HX} cy={hy} r={HUB_R} fill="none" stroke={branch.color} strokeWidth={1}>
                <animate attributeName="r" from={`${HUB_R}`} to={`${HUB_R + 14}`} dur="2.8s" repeatCount="indefinite" />
                <animate attributeName="opacity" from="0.6" to="0" dur="2.8s" repeatCount="indefinite" />
              </circle>
            )}
            <text x={HX} y={lblY} textAnchor="middle" className="cc-map-hub-lbl" style={{ fill: branch.color }}>
              {branch.label}
            </text>

            {/* cards */}
            {branch.cards.slice(0, ys.length).map((c, i) => {
              const cy = ys[i];
              return (
                <g key={`card-${c.id}`}>
                  <rect x={CARD_X} y={cy - CARD_H / 2} width={CARD_W} height={CARD_H} rx={10} className="cc-map-card" />
                  <rect x={CARD_X} y={cy - CARD_H / 2} width={3.5} height={CARD_H} rx={2} fill={c.color} />
                  <NumText value={c.value} x={CARD_X + 20} y={cy - 4} className="cc-map-card-val" style={{ fill: c.color }} />
                  <text x={CARD_X + 20} y={cy + 15} className="cc-map-card-lbl">
                    {c.label}
                  </text>
                </g>
              );
            })}
          </g>
        ))}
      </svg>
    </div>
  );
}
