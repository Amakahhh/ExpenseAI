"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import TransactionTable from "@/components/TransactionTable";
import { getTransactions, Transaction } from "@/lib/api";

function Skeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="skeleton h-12 rounded-xl" style={{ animationDelay: `${i * 0.06}s` }} />
      ))}
    </div>
  );
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);

  useEffect(() => {
    const sid = sessionStorage.getItem("session_id") ?? undefined;
    getTransactions(sid)
      .then(setTransactions)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen neural-grid" style={{ background: "#05050A" }}>
      <Navbar />
      <main className="max-w-7xl mx-auto px-6 py-8 animate-fade-focus">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-display font-bold text-2xl" style={{ color: "#F0F0FF" }}>
              Transactions
            </h1>
            {!loading && !error && (
              <p className="font-mono text-xs mt-1" style={{ color: "#6B6B8A" }}>
                {transactions.length} rows · click any row to expand &amp; correct
              </p>
            )}
          </div>
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-xs font-mono px-4 py-2 rounded-lg"
            style={{ background: "rgba(108,99,255,0.08)", color: "#6C63FF", border: "1px solid rgba(108,99,255,0.15)" }}
          >
            ← Dashboard
          </Link>
        </div>

        {loading ? (
          <Skeleton />
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <p className="font-mono text-sm" style={{ color: "#FF6B35" }}>{error}</p>
            <Link href="/" className="text-sm font-mono underline" style={{ color: "#6C63FF" }}>
              ← Upload a file first
            </Link>
          </div>
        ) : transactions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4 relative overflow-hidden">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="particle" style={{
                left: `${10 + Math.random() * 80}%`,
                top:  `${20 + Math.random() * 60}%`,
                "--dur":   `${3 + Math.random() * 3}s`,
                "--delay": `${Math.random() * 3}s`,
                "--dx":    `${(Math.random() - 0.5) * 60}px`,
              } as React.CSSProperties} />
            ))}
            <p className="font-display text-lg font-semibold" style={{ color: "#F0F0FF" }}>
              No transactions found
            </p>
            <p className="font-mono text-sm" style={{ color: "#6B6B8A" }}>
              Upload a bank statement to begin
            </p>
            <Link href="/" className="mt-2 text-sm font-mono underline" style={{ color: "#6C63FF" }}>
              Upload now →
            </Link>
          </div>
        ) : (
          <TransactionTable transactions={transactions} />
        )}
      </main>
    </div>
  );
}
