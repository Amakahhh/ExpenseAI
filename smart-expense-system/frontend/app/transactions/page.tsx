"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import TransactionTable from "@/components/TransactionTable";
import { getTransactions, Transaction, getToken } from "@/lib/api";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function TransactionsPage() {
  const router = useRouter();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) { router.replace("/login"); return; }
    const sid = sessionStorage.getItem("session_id") ?? undefined;
    getTransactions(sid)
      .then(setTransactions)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main className="page-content">

        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--ink)", letterSpacing: "-0.02em", marginBottom: 6 }}>
            All Transactions
          </h1>
          {!loading && !error && (
            <p style={{ fontSize: 13, color: "var(--muted)" }}>
              {transactions.length.toLocaleString()} transactions
            </p>
          )}
        </div>

        {loading ? (
          <div style={{ border: "1px solid var(--border)", borderRadius: 3, overflow: "hidden" }}>
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 50, borderRadius: 0, borderBottom: "1px solid var(--border)" }} />
            ))}
          </div>
        ) : error ? (
          <div style={{ paddingTop: 64, textAlign: "center" }}>
            <p className="error-box" style={{ display: "inline-block", marginBottom: 16 }}>{error}</p>
            <br />
            <Link href="/" style={{ color: "var(--ink)", fontWeight: 500, textDecoration: "underline" }}>Upload a file first</Link>
          </div>
        ) : transactions.length === 0 ? (
          <div style={{ paddingTop: 80, textAlign: "center" }}>
            <p style={{ fontSize: 15, color: "var(--muted)", marginBottom: 20 }}>No transactions found.</p>
            <Link href="/" className="btn-primary" style={{ display: "inline-flex" }}>Upload a bank statement</Link>
          </div>
        ) : (
          <TransactionTable transactions={transactions} />
        )}
      </main>
    </div>
  );
}
