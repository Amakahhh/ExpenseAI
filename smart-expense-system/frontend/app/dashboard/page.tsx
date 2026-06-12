"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import MonthlyChart from "@/components/MonthlyChart";
import CategoryChart from "@/components/CategoryChart";
import TransactionTable from "@/components/TransactionTable";
import { getAnalytics, getTransactions, getToken, getActiveSessionId, Analytics, Transaction } from "@/lib/api";
import { useRouter } from "next/navigation";

function fmtNaira(n: number) {
  return "₦" + (n ?? 0).toLocaleString("en-NG", { minimumFractionDigits: 2 });
}
function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}
function Skel({ h = 100, r = 8 }: { h?: number; r?: number }) {
  return <div className="skeleton" style={{ height: h, borderRadius: r }} />;
}

export default function DashboardPage() {
  const router = useRouter();
  const [data,  setData]  = useState<Analytics | null>(null);
  const [txs,   setTxs]   = useState<Transaction[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    const sid = getActiveSessionId() || sessionStorage.getItem("session_id") || undefined;
    Promise.all([getAnalytics(sid), getTransactions(sid)])
      .then(([analytics, transactions]) => { setData(analytics); setTxs(transactions); })
      .catch(() => {})
      .finally(() => setReady(true));
  }, [router]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main className="page-content">

        {!ready ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <Skel h={44} r={6} />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1 }}>
              <Skel h={90} r={0} /><Skel h={90} r={0} /><Skel h={90} r={0} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "58fr 42fr", gap: 24 }}>
              <Skel h={260} /><Skel h={260} />
            </div>
            <Skel h={300} />
          </div>
        ) : !data ? (
          <div style={{ paddingTop: 80, textAlign: "center" }}>
            <p style={{ fontSize: 15, color: "var(--muted)", marginBottom: 20 }}>No data yet. Upload a statement to get started.</p>
            <Link href="/" className="btn-primary" style={{ display: "inline-flex" }}>Upload now</Link>
          </div>
        ) : (
          <>
            {/* Greeting */}
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 6, fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)", letterSpacing: "0.02em" }}>
              {greeting()}
            </p>

            {/* Hero number */}
            <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 32 }}>
              <div>
                <p className="stat-label" style={{ marginBottom: 8 }}>Total spent</p>
                <p className="stat-value-large">{fmtNaira(data.total_spend)}</p>
              </div>
            </div>

            {/* Stat strip */}
            <div className="stat-grid">
              {[
                { label: "Total income",  value: fmtNaira(data.total_income)           },
                { label: "Transactions",  value: (data.total_count ?? 0).toLocaleString() },
                { label: "Top category",  value: data.by_category[0]?.category ?? "—"  },
              ].map(({ label, value }, i) => (
                <div key={label} style={{
                  borderLeft: i > 0 ? "1px solid var(--border)" : "none",
                }}>
                  <p className="stat-label" style={{ marginBottom: 10 }}>{label}</p>
                  <p style={{
                    fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)",
                    fontSize: 22,
                    color: "var(--ink)",
                    fontWeight: 700,
                    textTransform: i === 2 ? "capitalize" : undefined,
                    letterSpacing: "-0.02em",
                  }}>
                    {value}
                  </p>
                </div>
              ))}
            </div>

            {/* Charts */}
            <div className="dashboard-grid">
              <div className="glass-card" style={{ padding: "24px 24px 16px" }}>
                <p style={{ fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)", fontSize: 11, fontWeight: 700, color: "var(--ghost)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 20 }}>
                  Monthly spending
                </p>
                {data.by_month.length > 0
                  ? <MonthlyChart data={data.by_month} />
                  : <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ghost)", fontSize: 13 }}>No data yet</div>
                }
              </div>

              <div className="glass-card" style={{ padding: "24px 24px 16px" }}>
                <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 20 }}>
                  <p style={{ fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)", fontSize: 11, fontWeight: 700, color: "var(--ghost)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                    By category
                  </p>
                  <Link href="/analytics" style={{ fontSize: 11, color: "var(--ghost)", textDecoration: "none" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--ink)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--ghost)")}>
                    Full analytics →
                  </Link>
                </div>
                {data.by_category.length > 0
                  ? <CategoryChart data={data.by_category} />
                  : <p style={{ color: "var(--ghost)", fontSize: 13 }}>No data yet</p>
                }
              </div>
            </div>

            {/* All transactions with inline correction */}
            <div style={{ marginBottom: 8 }}>
              <p style={{
                fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)",
                fontSize: 11, fontWeight: 700, color: "var(--ghost)",
                letterSpacing: "0.1em", textTransform: "uppercase",
                marginBottom: 20,
              }}>
                Transactions
              </p>
              {txs.length === 0
                ? <p style={{ color: "var(--ghost)", fontSize: 13 }}>No transactions loaded.</p>
                : <TransactionTable transactions={txs} />
              }
            </div>
          </>
        )}
      </main>
    </div>
  );
}
