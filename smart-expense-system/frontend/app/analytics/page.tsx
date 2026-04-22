"use client";

import { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import MonthlyChart from "@/components/MonthlyChart";
import CategoryChart from "@/components/CategoryChart";
import { getAnalytics, Analytics } from "@/lib/api";
import { useCountUp } from "@/components/useCountUp";

// D3 graph is client-only
const MerchantGraph = dynamic(() => import("@/components/MerchantGraph"), { ssr: false });

const CAT_COLOR: Record<string, string> = {
  food:"#F59E0B", transport:"#00D4FF", entertainment:"#A855F7",
  bills:"#EF4444", health:"#EC4899", education:"#EAB308",
  shopping:"#F97316", other:"#6B6B8A",
};

function Skel({ h = "h-40" }: { h?: string }) {
  return <div className={`skeleton rounded-2xl ${h}`} />;
}

function AnimNum({ value, prefix = "" }: { value: number; prefix?: string }) {
  const n = useCountUp(value, 1400, 300);
  return <span className="holo-text font-mono font-bold tabular-nums">
    {prefix}{n.toLocaleString("en-NG")}
  </span>;
}

export default function AnalyticsPage() {
  const [data, setData]   = useState<Analytics | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const sid = sessionStorage.getItem("session_id") ?? undefined;
    getAnalytics(sid)
      .then((d) => { setData(d); setReady(true); })
      .catch(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <>
        <Navbar />
        <div className="max-w-7xl mx-auto px-6 py-8 space-y-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-8"><Skel h="h-[420px]" /></div>
            <div className="col-span-4 flex flex-col gap-4">
              <Skel h="h-32" /><Skel h="h-32" /><Skel h="h-32" />
            </div>
          </div>
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6"><Skel h="h-64" /></div>
            <div className="col-span-6"><Skel h="h-64" /></div>
          </div>
        </div>
      </>
    );
  }

  if (!data) {
    return (
      <>
        <Navbar />
        <div className="flex flex-col items-center justify-center h-[70vh] gap-4">
          <p className="font-mono text-sm" style={{ color: "#6B6B8A" }}>No data found.</p>
          <Link href="/" className="text-sm font-mono underline" style={{ color: "#6C63FF" }}>Upload a statement →</Link>
        </div>
      </>
    );
  }

  const topMerchant = data.top_merchants[0];

  return (
    <div className="min-h-screen neural-grid" style={{ background: "#05050A" }}>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-4 animate-fade-focus">

        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="font-display font-bold text-2xl" style={{ color: "#F0F0FF" }}>Analytics</h1>
            <p className="font-mono text-xs mt-1" style={{ color: "#6B6B8A" }}>
              Merchant graph · category treemap · spend velocity
            </p>
          </div>
          <Link href="/dashboard"
            className="text-xs font-mono px-4 py-2 rounded-lg"
            style={{ background: "rgba(108,99,255,0.08)", color: "#6C63FF", border: "1px solid rgba(108,99,255,0.15)" }}>
            ← Dashboard
          </Link>
        </div>

        {/* ROW 1 — GNN Merchant Graph + stat satellites */}
        <div className="grid grid-cols-12 gap-4">

          {/* Merchant graph */}
          <div className="col-span-12 lg:col-span-8 card p-5 animate-slide-up delay-1"
            style={{ height: 420 }}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="font-display font-semibold text-sm" style={{ color: "#F0F0FF" }}>
                  Merchant Similarity Graph
                </p>
                <p className="font-mono text-xs mt-0.5" style={{ color: "#6B6B8A" }}>
                  GNN-inspired · drag nodes · hover for details
                </p>
              </div>
              {/* Legend */}
              <div className="flex flex-wrap gap-2">
                {Object.entries(CAT_COLOR).slice(0, 5).map(([cat, color]) => (
                  <span key={cat} className="flex items-center gap-1 text-[10px] font-mono capitalize"
                    style={{ color: "#6B6B8A" }}>
                    <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />
                    {cat}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ height: "calc(100% - 52px)" }}>
              {data.top_merchants.length > 0 ? (
                <MerchantGraph merchants={data.top_merchants} />
              ) : (
                <div className="h-full flex items-center justify-center font-mono text-sm"
                  style={{ color: "#6B6B8A" }}>No merchant data</div>
              )}
            </div>
          </div>

          {/* Stat satellites */}
          <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">

            <div className="card p-5 animate-slide-up delay-2">
              <p className="font-mono text-xs uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>Total Spend</p>
              <div style={{ fontSize: "clamp(1.6rem,4vw,2.2rem)", lineHeight: 1 }}>
                <AnimNum value={data.total_spend} prefix="₦" />
              </div>
              <p className="font-mono text-xs mt-2" style={{ color: "#6B6B8A" }}>
                {data.transaction_count} debit · {data.income_count} credit
              </p>
            </div>

            <div className="card p-5 animate-slide-up delay-3">
              <p className="font-mono text-xs uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>Top Merchant</p>
              {topMerchant ? (
                <>
                  <p className="font-display font-semibold text-base truncate" style={{ color: "#F0F0FF" }}>
                    {topMerchant.merchant}
                  </p>
                  <p className="font-mono text-sm mt-1" style={{ color: "#00D4FF" }}>
                    ₦{topMerchant.total.toLocaleString("en-NG")}
                  </p>
                  <p className="font-mono text-xs mt-1" style={{ color: "#6B6B8A" }}>
                    {topMerchant.count} transactions
                  </p>
                </>
              ) : <p className="font-mono text-sm" style={{ color: "#6B6B8A" }}>—</p>}
            </div>

            <div className="card p-5 animate-slide-up delay-4">
              <p className="font-mono text-xs uppercase tracking-widest mb-3" style={{ color: "#6B6B8A" }}>Category Mix</p>
              <div className="space-y-2">
                {data.by_category.slice(0, 4).map((c) => {
                  const pct   = data.total_spend > 0 ? (c.total / data.total_spend) * 100 : 0;
                  const color = CAT_COLOR[c.category] || "#6B6B8A";
                  return (
                    <div key={c.category} className="flex items-center gap-2">
                      <span className="w-16 font-mono text-[10px] capitalize truncate" style={{ color }}>{c.category}</span>
                      <div className="flex-1 conf-bar-track">
                        <div className="conf-bar-fill" style={{ width: `${pct}%`, background: color }} />
                      </div>
                      <span className="font-mono text-[10px] w-8 text-right" style={{ color: "#6B6B8A" }}>
                        {pct.toFixed(0)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ROW 2 — Category treemap + Monthly area */}
        <div className="grid grid-cols-12 gap-4">

          <div className="col-span-12 lg:col-span-6 card p-5 animate-slide-up delay-3">
            <p className="font-display font-semibold text-sm mb-1" style={{ color: "#F0F0FF" }}>
              Spend by Category
            </p>
            <p className="font-mono text-xs mb-4" style={{ color: "#6B6B8A" }}>
              Proportional treemap · hover to inspect
            </p>
            {data.by_category.length > 0
              ? <CategoryChart data={data.by_category} />
              : <div className="h-56 flex items-center justify-center font-mono text-xs" style={{ color: "#6B6B8A" }}>No data</div>}
          </div>

          <div className="col-span-12 lg:col-span-6 card p-5 animate-slide-up delay-4">
            <p className="font-display font-semibold text-sm mb-1" style={{ color: "#F0F0FF" }}>
              Spend Velocity
            </p>
            <p className="font-mono text-xs mb-4" style={{ color: "#6B6B8A" }}>
              Monthly debit trend · glowing area
            </p>
            {data.by_month.length > 0
              ? <MonthlyChart data={data.by_month} />
              : <div className="h-52 flex items-center justify-center font-mono text-xs" style={{ color: "#6B6B8A" }}>No data</div>}
          </div>
        </div>

        {/* ROW 3 — Lollipop merchant chart */}
        {data.top_merchants.length > 0 && (
          <div className="card p-6 animate-slide-up delay-5">
            <p className="font-display font-semibold text-sm mb-6" style={{ color: "#F0F0FF" }}>
              Merchant Leaderboard
            </p>
            <div className="space-y-5">
              {data.top_merchants.map((m, i) => {
                const pct   = data.top_merchants[0].total > 0
                  ? (m.total / data.top_merchants[0].total) * 100 : 0;
                const color = CAT_COLOR[(m as any).category] || "#6C63FF";
                return (
                  <div key={i} className="flex items-center gap-4">
                    <span className="font-mono text-xs w-5 text-right shrink-0" style={{ color: "#6B6B8A" }}>
                      {i + 1}
                    </span>
                    <div className="w-44 shrink-0">
                      <p className="font-mono text-xs truncate" style={{ color: "#F0F0FF" }} title={m.merchant}>
                        {m.merchant}
                      </p>
                      <p className="font-mono text-[10px] capitalize mt-0.5" style={{ color }}>
                        {(m as any).category || "—"} · {m.count}×
                      </p>
                    </div>
                    {/* Lollipop */}
                    <div className="flex-1 flex items-center gap-2">
                      <div
                        className="lollipop-line"
                        style={{ width: `${pct}%`, minWidth: 4 }}
                      />
                      <div
                        className="lollipop-dot"
                        style={{ background: color, boxShadow: `0 0 10px ${color}70` }}
                      />
                    </div>
                    <span className="font-mono text-sm shrink-0" style={{ color: "#F0F0FF" }}>
                      ₦{m.total.toLocaleString("en-NG", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
