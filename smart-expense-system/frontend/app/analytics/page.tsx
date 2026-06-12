"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Sidebar from "@/components/Sidebar";
import { getAnalytics, Analytics, getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";

const MerchantGraph = dynamic(() => import("@/components/MerchantGraph"), { ssr: false });

function Skel({ h = 100 }: { h?: number }) {
  return <div className="skeleton" style={{ height: h, borderRadius: 3 }} />;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [data,  setData]  = useState<Analytics | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    const sid = sessionStorage.getItem("session_id") ?? undefined;
    getAnalytics(sid).then((d) => { setData(d); setReady(true); }).catch(() => setReady(true));
  }, [router]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main className="page-content">

        {!ready ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <Skel h={40} /><Skel h={480} /><Skel h={360} />
          </div>
        ) : !data ? (
          <div style={{ paddingTop: 80, textAlign: "center" }}>
            <p style={{ fontSize: 15, color: "var(--muted)", marginBottom: 20 }}>No data loaded yet.</p>
            <Link href="/" className="btn-primary" style={{ display: "inline-flex" }}>Upload a bank statement</Link>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 36 }}>
              <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--ink)", letterSpacing: "-0.02em", marginBottom: 6 }}>
                Merchant Analytics
              </h1>
              <p style={{ fontSize: 13, color: "var(--muted)" }}>Merchant similarity graph and spending breakdown</p>
            </div>

            {/* Merchant graph */}
            <div style={{ border: "1px solid var(--border)", borderRadius: 3, padding: 28, marginBottom: 40, background: "var(--surface)" }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 24 }}>
                <div>
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--ink)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    Merchant similarity graph
                  </p>
                  <p style={{ fontSize: 11, color: "var(--ghost)", marginTop: 4 }}>
                    Connected by spending category · drag nodes to explore
                  </p>
                </div>
              </div>
              <div style={{ height: 480, background: "#FFFFFF", border: "1px solid var(--border)", borderRadius: 2 }}>
                {data.top_merchants.length > 0
                  ? <MerchantGraph merchants={data.top_merchants} />
                  : <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ghost)", fontSize: 13 }}>No merchant data</div>
                }
              </div>
            </div>

            {/* Top merchants ranked list */}
            {data.top_merchants.length > 0 && (
              <div>
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--ink)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 20 }}>
                  Top merchants by spend
                </p>
                <div style={{ border: "1px solid var(--border)", borderRadius: 3, overflow: "hidden", background: "var(--page)" }}>
                  {data.top_merchants.slice(0, 10).map((m, i) => {
                    const pct = data.top_merchants[0].total > 0
                      ? (m.total / data.top_merchants[0].total) * 100 : 0;
                    return (
                      <div key={i} style={{ padding: "16px 24px", borderBottom: i < 9 ? "1px solid var(--border)" : "none" }}>
                        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 8 }}>
                          <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
                            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent)", width: 16, flexShrink: 0, fontFamily: "var(--font-mono)" }}>
                              {i + 1}
                            </span>
                            <span className="serif" style={{ fontSize: 15, color: "var(--ink)" }}>
                              {m.merchant}
                            </span>
                          </div>
                          <span style={{ fontSize: 13, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                            ₦{m.total.toLocaleString("en-NG", { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                        <div style={{ marginLeft: 32 }}>
                          <div style={{ height: 1, background: "var(--border)", overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${pct}%`, background: "var(--ink)" }} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
