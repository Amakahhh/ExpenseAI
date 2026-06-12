"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getSessionHistory, setActiveSessionId, saveStoredSession, SessionRecord } from "@/lib/api";

function fmtN(n: number) {
  return new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", minimumFractionDigits: 0 }).format(n);
}

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export default function SessionHistory() {
  const [records, setRecords] = useState<SessionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getSessionHistory().then(setRecords).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading || records.length === 0) return null;

  function open(rec: SessionRecord) {
    setActiveSessionId(rec.session_id);
    sessionStorage.setItem("session_id", rec.session_id);
    saveStoredSession({
      session_id: rec.session_id,
      filename: rec.filename,
      upload_date: rec.upload_date,
      total_transactions: rec.total_transactions,
      total_spend: rec.total_spend,
    });
    router.push("/dashboard");
  }

  return (
    <div style={{ marginTop: 28 }}>
      <p style={{ fontSize: 10, fontWeight: 700, color: "var(--ghost)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>
        Previous uploads
      </p>
      <div className="card" style={{ display: "flex", flexDirection: "column", overflow: "hidden", padding: 0 }}>
        {records.slice(0, 5).map((rec, i) => (
          <button
            key={rec.session_id}
            onClick={() => open(rec)}
            style={{
              width: "100%",
              textAlign: "left",
              background: "var(--page)",
              border: "none",
              borderTop: i > 0 ? "1px solid var(--border)" : "none",
              padding: "12px 16px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              transition: "background 0.1s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "var(--page)")}
          >
            <div style={{ minWidth: 0 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {rec.filename || "Bank statement"}
              </p>
              <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2, fontFamily: "var(--font-mono, monospace)" }}>
                {fmtDate(rec.upload_date)} · {rec.total_transactions} transactions
              </p>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", fontFamily: "var(--font-mono, monospace)" }}>{fmtN(rec.total_spend)}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
