"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import CategoryChart from "@/components/CategoryChart";
import MonthlyChart from "@/components/MonthlyChart";
import { getAnalytics, getTransactions, Analytics, Transaction } from "@/lib/api";
import { useCountUp } from "@/components/useCountUp";

const CAT_COLOR: Record<string, string> = {
  food:"#F59E0B", transport:"#00D4FF", entertainment:"#A855F7",
  bills:"#EF4444", health:"#EC4899", education:"#EAB308",
  shopping:"#F97316", other:"#6B6B8A",
};

/* ── Skeleton card ──────────────────────────────────────────────────────── */
function Skel({ h = "h-32" }: { h?: string }) {
  return <div className={`skeleton rounded-2xl ${h}`} />;
}

/* ── Animated number ────────────────────────────────────────────────────── */
function AnimNum({ value, prefix = "", delay = 0 }: { value: number; prefix?: string; delay?: number }) {
  const n = useCountUp(value, 1400, delay);
  return (
    <span className="holo-text font-mono font-bold tabular-nums">
      {prefix}{n.toLocaleString("en-NG", { minimumFractionDigits: 0 })}
    </span>
  );
}

/* ── Arc confidence gauge ───────────────────────────────────────────────── */
function ArcGauge({ pct, color }: { pct: number; color: string }) {
  const r = 22, c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <svg width="56" height="56" viewBox="0 0 56 56" className="-rotate-90">
      <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3.5" />
      <circle cx="28" cy="28" r={r} fill="none" stroke={color} strokeWidth="3.5"
        strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset}
        style={{ transition: "stroke-dashoffset 1s ease" }} />
    </svg>
  );
}

/* ── Live feed row ──────────────────────────────────────────────────────── */
function FeedRow({ tx, i }: { tx: Transaction; i: number }) {
  const cat   = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
  const color = CAT_COLOR[cat] || "#6B6B8A";
  return (
    <div
      className="flex items-center gap-3 py-2.5 border-b animate-slide-up"
      style={{ borderColor: "rgba(108,99,255,0.08)", animationDelay: `${i * 0.06}s` }}
    >
      <div className="w-1.5 h-7 rounded-full shrink-0" style={{ background: color }} />
      <p className="flex-1 text-xs truncate" style={{ color: "#F0F0FF" }}>{tx.description}</p>
      <span
        className="text-[10px] font-mono px-1.5 py-0.5 rounded-full capitalize shrink-0"
        style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
      >
        {cat}
      </span>
      <span className="font-mono text-xs shrink-0"
        style={{ color: tx.transaction_type === "credit" ? "#00E5A0" : "#F0F0FF" }}>
        ₦{(tx.amount || 0).toLocaleString("en-NG", { maximumFractionDigits: 0 })}
      </span>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData]   = useState<Analytics | null>(null);
  const [txs,  setTxs]    = useState<Transaction[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const sid = sessionStorage.getItem("session_id") ?? undefined;
    Promise.all([getAnalytics(sid), getTransactions(sid)])
      .then(([analytics, transactions]) => {
        setData(analytics);
        setTxs(transactions.slice(0, 12));
        setReady(true);
      })
      .catch(() => setReady(true));
  }, []);

  /* ── Loading skeletons ─────────────────────────────────────────────── */
  if (!ready) {
    return (
      <>
        <Navbar />
        <div className="max-w-7xl mx-auto px-6 py-8 space-y-4">
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-7"><Skel h="h-64" /></div>
            <div className="col-span-5"><Skel h="h-64" /></div>
          </div>
          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-6"><Skel h="h-52" /></div>
            <div className="col-span-3"><Skel h="h-52" /></div>
            <div className="col-span-3"><Skel h="h-52" /></div>
          </div>
          <Skel h="h-40" />
        </div>
      </>
    );
  }

  if (!data) {
    return (
      <>
        <Navbar />
        <div className="flex flex-col items-center justify-center h-[70vh] gap-4">
          <p className="font-display text-lg" style={{ color: "#6B6B8A" }}>No data found.</p>
          <Link href="/" className="text-sm underline" style={{ color: "#6C63FF" }}>Upload a statement →</Link>
        </div>
      </>
    );
  }

  const lowConf = txs.filter((t) => t.confidence < 0.7);
  const topCat  = data.by_category[0];

  return (
    <div className="min-h-screen neural-grid" style={{ background: "#05050A" }}>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between mb-2 animate-slide-up">
          <div>
            <h1 className="font-display font-bold text-2xl" style={{ color: "#F0F0FF" }}>
              Spending Dashboard
            </h1>
            <p className="text-xs font-mono mt-1" style={{ color: "#6B6B8A" }}>
              {data.total_count} rows processed · {data.transaction_count} debits · {data.income_count} credits
            </p>
          </div>
          <Link
            href="/transactions"
            className="flex items-center gap-1.5 text-xs font-mono px-4 py-2 rounded-lg transition-colors"
            style={{ background: "rgba(108,99,255,0.1)", color: "#6C63FF", border: "1px solid rgba(108,99,255,0.2)" }}
          >
            View transactions →
          </Link>
        </div>

        {/* ROW 1 — Hero spend + Live feed */}
        <div className="grid grid-cols-12 gap-4">

          {/* Hero spend card */}
          <div className="col-span-12 lg:col-span-7 card p-6 animate-slide-up delay-1">
            <div className="flex items-start justify-between mb-6">
              <div>
                <p className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>
                  Total Debit
                </p>
                <div style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", lineHeight: 1 }}>
                  <AnimNum value={data.total_spend} prefix="₦" delay={200} />
                </div>
                <p className="text-xs font-mono mt-2" style={{ color: "#6B6B8A" }}>
                  excl. OWealth transfers
                </p>
              </div>
              {data.total_income > 0 && (
                <div className="text-right">
                  <p className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>
                    Total Credit
                  </p>
                  <p className="font-mono font-bold text-2xl" style={{ color: "#00E5A0" }}>
                    ₦{data.total_income.toLocaleString("en-NG")}
                  </p>
                </div>
              )}
            </div>

            {/* Category treemap */}
            {data.by_category.length > 0 ? (
              <CategoryChart data={data.by_category} />
            ) : (
              <div className="h-56 flex items-center justify-center" style={{ color: "#6B6B8A" }}>
                <p className="text-sm">No category data yet</p>
              </div>
            )}
          </div>

          {/* Live feed */}
          <div className="col-span-12 lg:col-span-5 card p-5 animate-slide-up delay-2 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <p className="font-display font-semibold text-sm" style={{ color: "#F0F0FF" }}>
                Transaction Feed
              </p>
              <span
                className="flex items-center gap-1.5 text-xs font-mono px-2 py-0.5 rounded-full"
                style={{ background: "rgba(0,229,160,0.08)", color: "#00E5A0" }}
              >
                <span className="w-1.5 h-1.5 rounded-full animate-pulse inline-block" style={{ background: "#00E5A0" }} />
                live
              </span>
            </div>
            <div className="flex-1 overflow-hidden">
              {txs.length === 0 ? (
                <p className="text-xs" style={{ color: "#6B6B8A" }}>No transactions loaded.</p>
              ) : (
                txs.map((tx, i) => <FeedRow key={tx.id} tx={tx} i={i} />)
              )}
            </div>
          </div>
        </div>

        {/* ROW 2 — Monthly + Confidence + Quick stats */}
        <div className="grid grid-cols-12 gap-4">

          {/* Monthly chart */}
          <div className="col-span-12 lg:col-span-6 card p-5 animate-slide-up delay-3">
            <p className="font-display font-semibold text-sm mb-1" style={{ color: "#F0F0FF" }}>
              Monthly Spend
            </p>
            <p className="text-xs font-mono mb-4" style={{ color: "#6B6B8A" }}>
              Total debit per month
            </p>
            {data.by_month.length > 0
              ? <MonthlyChart data={data.by_month} />
              : <div className="h-52 flex items-center justify-center text-xs" style={{ color: "#6B6B8A" }}>No monthly data</div>
            }
          </div>

          {/* Confidence breakdown */}
          <div className="col-span-12 lg:col-span-3 card p-5 animate-slide-up delay-4">
            <p className="font-display font-semibold text-sm mb-4" style={{ color: "#F0F0FF" }}>
              AI Confidence
            </p>
            <div className="space-y-3">
              {txs.slice(0, 5).map((tx) => {
                const cat   = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
                const color = tx.confidence < 0.7 ? "#FF6B35" : "#00E5A0";
                const pct   = Math.round(tx.confidence * 100);
                return (
                  <div key={tx.id} className="flex items-center gap-3">
                    <ArcGauge pct={pct} color={color} />
                    <div className="min-w-0">
                      <p className="text-[10px] truncate" style={{ color: "#6B6B8A" }}>
                        {tx.description.slice(0, 22)}…
                      </p>
                      <p className="font-mono text-xs font-semibold capitalize mt-0.5"
                        style={{ color }}>
                        {cat} · {pct}%
                      </p>
                      {tx.confidence < 0.7 && (
                        <span className="text-[9px] font-mono px-1 py-0.5 rounded"
                          style={{ background: "rgba(255,107,53,0.1)", color: "#FF6B35" }}>
                          Review
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stats satellites */}
          <div className="col-span-12 lg:col-span-3 flex flex-col gap-4 animate-slide-up delay-5">
            <div className="card p-5 flex-1">
              <p className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>Top Category</p>
              {topCat ? (
                <>
                  <p className="font-display font-bold text-xl capitalize mb-1"
                    style={{ color: CAT_COLOR[topCat.category] || "#6C63FF" }}>
                    {topCat.category}
                  </p>
                  <p className="font-mono text-sm" style={{ color: "#F0F0FF" }}>
                    ₦{topCat.total.toLocaleString("en-NG")}
                  </p>
                  <p className="text-xs font-mono mt-1" style={{ color: "#6B6B8A" }}>
                    {topCat.count} transactions
                  </p>
                </>
              ) : <p className="text-xs" style={{ color: "#6B6B8A" }}>—</p>}
            </div>

            <div className="card p-5 flex-1">
              <p className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: "#6B6B8A" }}>
                Review Needed
              </p>
              <p className="holo-text font-mono font-bold text-3xl">{lowConf.length}</p>
              <p className="text-xs font-mono mt-1" style={{ color: "#6B6B8A" }}>
                confidence &lt; 70%
              </p>
              {lowConf.length > 0 && (
                <Link href="/transactions" className="mt-2 text-xs font-mono inline-block underline"
                  style={{ color: "#FF6B35" }}>
                  Review →
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* ROW 3 — Top Merchants */}
        {data.top_merchants.length > 0 && (
          <div className="card p-6 animate-slide-up delay-6">
            <div className="flex items-center justify-between mb-6">
              <p className="font-display font-semibold" style={{ color: "#F0F0FF" }}>Top Merchants</p>
              <Link href="/analytics" className="text-xs font-mono" style={{ color: "#6C63FF" }}>
                Graph view →
              </Link>
            </div>
            <div className="space-y-4">
              {data.top_merchants.slice(0, 8).map((m, i) => {
                const pct   = data.top_merchants[0].total > 0
                  ? (m.total / data.top_merchants[0].total) * 100 : 0;
                const color = CAT_COLOR[(m as any).category] || "#6C63FF";
                return (
                  <div key={i} className="flex items-center gap-4">
                    <span className="font-mono text-xs w-4 text-right shrink-0" style={{ color: "#6B6B8A" }}>
                      {i + 1}
                    </span>
                    <span className="text-sm w-48 truncate shrink-0" style={{ color: "#F0F0FF" }} title={m.merchant}>
                      {m.merchant}
                    </span>
                    {/* Lollipop */}
                    <div className="flex-1 flex items-center gap-2">
                      <div className="lollipop-line" style={{ width: `${pct}%` }} />
                      <div className="lollipop-dot" style={{ background: color, boxShadow: `0 0 8px ${color}60` }} />
                    </div>
                    <span className="font-mono text-sm shrink-0" style={{ color: "#F0F0FF" }}>
                      ₦{m.total.toLocaleString("en-NG")}
                    </span>
                    <span className="font-mono text-xs shrink-0" style={{ color: "#6B6B8A" }}>
                      {m.count}×
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
