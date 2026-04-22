"use client";
import { useEffect, useRef, useState } from "react";

const easeOutQuart = (t: number) => 1 - Math.pow(1 - t, 4);

export function useCountUp(target: number, duration = 1400, delay = 0): number {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (target === 0) { setValue(0); return; }

    const startAt = performance.now() + delay;

    const tick = (now: number) => {
      if (now < startAt) { rafRef.current = requestAnimationFrame(tick); return; }
      const progress = Math.min((now - startAt) / duration, 1);
      setValue(Math.round(easeOutQuart(progress) * target));
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration, delay]);

  return value;
}
