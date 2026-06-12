"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, setToken } from "@/lib/api";
import { LogoFull } from "@/components/Logo";

export default function LoginPage() {
  const router = useRouter();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      setToken(res.access_token, res.user_email, res.user_name);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Incorrect email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-layout">

      {/* Dark panel */}
      <div className="auth-panel-dark">
        <LogoFull size={28} dark />

        <div>
          <p style={{ fontFamily: "var(--font-display, 'Plus Jakarta Sans', sans-serif)", fontSize: "clamp(30px, 3vw, 42px)", fontWeight: 800, color: "#FFFFFF", lineHeight: 1.12, letterSpacing: "-0.04em", marginBottom: 20 }}>
            Understand your<br />money, clearly.
          </p>
          <p style={{ fontSize: 14, color: "#555555", lineHeight: 1.75, maxWidth: 320 }}>
            Upload a bank statement and get instant AI categorisation, merchant analysis, and visual breakdowns.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {["AI-powered, no manual tagging needed", "Correct misclassifications with one click", "Your data stays private and secure"].map((t) => (
            <div key={t} style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#C07A10", flexShrink: 0, marginTop: 6 }} />
              <p style={{ fontSize: 13, color: "#555555", lineHeight: 1.5 }}>{t}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Light panel */}
      <div className="auth-panel-light">
        <div style={{ width: "100%", maxWidth: 380 }}>

          <div style={{ marginBottom: 40 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--ink)", letterSpacing: "-0.03em", marginBottom: 8 }}>
              Welcome back
            </h1>
            <p style={{ fontSize: 14, color: "var(--muted)" }}>Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                Email
              </label>
              <input
                type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-field"
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                Password
              </label>
              <input
                type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="input-field"
              />
            </div>

            {error && <p className="error-box">{error}</p>}

            <button type="submit" disabled={loading} className="btn-primary" style={{ width: "100%", marginTop: 4, padding: "12px" }}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p style={{ marginTop: 28, fontSize: 13, color: "var(--muted)" }}>
            No account?{" "}
            <Link href="/signup" style={{ color: "var(--ink)", fontWeight: 600, textDecoration: "underline" }}>
              Create one
            </Link>
          </p>
        </div>
      </div>

    </div>
  );
}
