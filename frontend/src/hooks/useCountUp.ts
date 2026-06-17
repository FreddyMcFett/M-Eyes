import { useEffect, useRef, useState } from 'react';

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Animates a number from its previous value to `target` with an ease-out cubic.
 * Honours `prefers-reduced-motion` by snapping straight to the target.
 */
export function useCountUp(target: number, ms = 1100): number {
  // With no DOM / no animation frames (server render, reduced motion) start at
  // the final value so the number is correct without the count-up tween.
  const [val, setVal] = useState(() =>
    typeof window === 'undefined' || prefersReducedMotion() ? target : 0,
  );
  const fromRef = useRef(0);
  const rafRef = useRef<number>();

  useEffect(() => {
    if (prefersReducedMotion()) {
      fromRef.current = target;
      setVal(target);
      return;
    }
    const from = fromRef.current;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(from + (target - from) * eased);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [target, ms]);

  return val;
}
