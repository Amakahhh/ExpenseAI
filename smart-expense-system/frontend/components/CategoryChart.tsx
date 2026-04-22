"use client";

import { CategoryStat } from "@/lib/api";
import { useMemo } from "react";

const CAT_COLORS: Record<string, string> = {
  food:          "#F59E0B",
  transport:     "#00D4FF",
  entertainment: "#A855F7",
  bills:         "#EF4444",
  health:        "#EC4899",
  education:     "#EAB308",
  shopping:      "#F97316",
  other:         "#6B6B8A",
};

interface Props { data: CategoryStat[] }

/** Simple proportional treemap using nested flex boxes */
export default function CategoryChart({ data }: Props) {
  const sorted = useMemo(
    () => [...data].sort((a, b) => b.total - a.total),
    [data],
  );
  const total = useMemo(() => sorted.reduce((s, d) => s + d.total, 0) || 1, [sorted]);

  const fmt = (v: number) =>
    v >= 1_000_000
      ? `₦${(v / 1_000_000).toFixed(1)}M`
      : v >= 1_000
      ? `₦${(v / 1_000).toFixed(0)}k`
      : `₦${v.toFixed(0)}`;

  return (
    <div className="w-full h-56 flex gap-1">
      {/* Large block — top 2 stacked */}
      <div className="flex flex-col gap-1" style={{ flex: (sorted[0]?.total || 0) + (sorted[1]?.total || 0) }}>
        {sorted.slice(0, 2).map((d) => (
          <TreeCell key={d.category} d={d} total={total} fmt={fmt} flex={d.total} />
        ))}
      </div>
      {/* Medium column — items 3-4 */}
      {sorted.length > 2 && (
        <div className="flex flex-col gap-1" style={{ flex: (sorted[2]?.total || 0) + (sorted[3]?.total || 0) }}>
          {sorted.slice(2, 4).map((d) => (
            <TreeCell key={d.category} d={d} total={total} fmt={fmt} flex={d.total} />
          ))}
        </div>
      )}
      {/* Small column — rest */}
      {sorted.length > 4 && (
        <div className="flex flex-col gap-1" style={{ flex: sorted.slice(4).reduce((s, d) => s + d.total, 0) }}>
          {sorted.slice(4).map((d) => (
            <TreeCell key={d.category} d={d} total={total} fmt={fmt} flex={d.total} small />
          ))}
        </div>
      )}
    </div>
  );
}

function TreeCell({
  d, total, fmt, flex, small = false,
}: {
  d: CategoryStat; total: number; fmt: (v: number) => string; flex: number; small?: boolean;
}) {
  const color = CAT_COLORS[d.category] || "#6B6B8A";
  const pct   = ((d.total / total) * 100).toFixed(1);

  return (
    <div
      className="treemap-cell relative group"
      style={{
        flex,
        background: `${color}18`,
        border: `1px solid ${color}30`,
        padding: small ? "6px 8px" : "10px 12px",
      }}
    >
      {/* Glow accent bar */}
      <div
        className="absolute top-0 left-0 w-full h-0.5 rounded-t"
        style={{ background: `linear-gradient(90deg, ${color}, transparent)` }}
      />

      <p
        className="font-display font-semibold capitalize leading-none mb-1"
        style={{ color, fontSize: small ? 10 : 12 }}
      >
        {d.category}
      </p>
      {!small && (
        <p className="font-mono font-bold" style={{ color: "#F0F0FF", fontSize: 13 }}>
          {fmt(d.total)}
        </p>
      )}
      <p className="font-mono" style={{ color: "#6B6B8A", fontSize: 10 }}>
        {pct}%
      </p>

      {/* Hover tooltip */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center rounded"
        style={{ background: `${color}22`, backdropFilter: "blur(4px)" }}
      >
        <p className="font-display text-xs font-bold capitalize" style={{ color }}>{d.category}</p>
        <p className="font-mono text-xs font-semibold" style={{ color: "#F0F0FF" }}>{fmt(d.total)}</p>
        <p className="font-mono text-xs" style={{ color: "#6B6B8A" }}>{d.count} txns · {pct}%</p>
      </div>
    </div>
  );
}
