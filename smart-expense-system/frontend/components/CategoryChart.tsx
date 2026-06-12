"use client";
import { useMemo } from "react";
import { CategoryStat } from "@/lib/api";

function fmt(v: number) {
  return v >= 1_000_000 ? `₦${(v / 1_000_000).toFixed(1)}M`
    : v >= 1_000 ? `₦${(v / 1_000).toFixed(0)}k`
    : `₦${v.toFixed(0)}`;
}

export default function CategoryChart({ data }: { data: CategoryStat[] }) {
  const sorted = useMemo(() => [...data].sort((a, b) => b.total - a.total), [data]);
  const max    = useMemo(() => Math.max(...sorted.map((d) => d.total), 1), [sorted]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {sorted.map((d, i) => {
        const pct = (d.total / max) * 100;
        return (
          <div key={d.category} style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 0", borderBottom: i < sorted.length - 1 ? "1px solid var(--border)" : "none" }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: "var(--accent)", width: 16, flexShrink: 0, fontFamily: "var(--font-mono, monospace)" }}>
              {i + 1}
            </span>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink)", width: 88, flexShrink: 0, textTransform: "capitalize" }}>
              {d.category}
            </span>
            <div style={{ flex: 1, height: 1, background: "var(--border)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${pct}%`, background: "var(--ink)", transition: "width 0.8s cubic-bezier(0.22,1,0.36,1)" }} />
            </div>
            <span style={{ fontSize: 12, color: "var(--muted)", flexShrink: 0, width: 60, textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>
              {fmt(d.total)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
