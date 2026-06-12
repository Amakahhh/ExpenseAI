"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import FileUpload from "@/components/FileUpload";
import SessionHistory from "@/components/SessionHistory";
import { getToken } from "@/lib/api";
import { LogoFull } from "@/components/Logo";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => { if (!getToken()) router.replace("/login"); }, [router]);
  if (typeof window !== "undefined" && !getToken()) return null;

  return (
    <main className="landing-page">

      {/* Header */}
      <header style={{
        maxWidth: 1000, margin: "0 auto",
        padding: "22px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "relative", zIndex: 1,
      }}>
        <LogoFull size={28} />
        <nav style={{ display: "flex", gap: 28, alignItems: "center", fontSize: 13, fontWeight: 500 }} className="hero-nav">
          <Link href="/dashboard"    style={{ color: "var(--muted)", textDecoration: "none" }}>Dashboard</Link>
          <Link href="/transactions" style={{ color: "var(--muted)", textDecoration: "none" }}>Transactions</Link>
          <Link href="/analytics"    style={{ color: "var(--muted)", textDecoration: "none" }}>Analytics</Link>
        </nav>
        <Link href="/dashboard" className="btn-primary" style={{ fontSize: 12, padding: "8px 16px" }}>
          Dashboard →
        </Link>
      </header>

      {/* Hero — centred upload focus */}
      <section style={{
        maxWidth: 600, margin: "0 auto",
        padding: "80px 32px 60px",
        display: "flex", flexDirection: "column", alignItems: "center",
        textAlign: "center",
        position: "relative", zIndex: 1,
      }}>
        <p className="hero-eyebrow">AI expense intelligence</p>
        <h1 className="hero-headline">
          Your money,<br />finally clear.
        </h1>
        <p style={{ maxWidth: 380, fontSize: 15, lineHeight: 1.75, color: "var(--muted)", marginBottom: 40 }}>
          Upload a bank statement and get instant AI categorisation, spending charts, and merchant insights.
        </p>

        <div className="upload-panel" style={{ width: "100%", maxWidth: 480 }}>
          <FileUpload />
        </div>

        <div style={{ width: "100%", maxWidth: 480, marginTop: 32 }}>
          <SessionHistory />
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        position: "relative", zIndex: 1,
        maxWidth: 1000, margin: "0 auto",
        padding: "24px 32px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        borderTop: "1px solid var(--border)",
      }}>
        <p style={{ fontSize: 12, color: "var(--ghost)" }}>© 2024 ExpenseAI</p>
        <p style={{ fontSize: 12, color: "var(--ghost)" }}>
          <Link href="/dashboard" style={{ color: "var(--ghost)", textDecoration: "none" }}>Dashboard</Link>
          {" · "}
          <Link href="/analytics" style={{ color: "var(--ghost)", textDecoration: "none" }}>Analytics</Link>
        </p>
      </footer>
    </main>
  );
}
