"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup, setToken } from "@/lib/api";
import { LogoFull } from "@/components/Logo";

export default function SignupPage() {
  const router = useRouter();
  const [fullName,  setFullName]  = useState("");
  const [email,     setEmail]     = useState("");
  const [password,  setPassword]  = useState("");
  const [error,     setError]     = useState("");
  const [loading,   setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 6) { setError("Password must be at least 6 characters."); return; }
    setLoading(true);
    try {
      const res = await signup(fullName, email, password);
      setToken(res.access_token, res.user_email, res.user_name);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Could not create account.");
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
            Start understanding<br />your money.
          </p>
          <p style={{ fontSize: 14, color: "#555555", lineHeight: 1.75, maxWidth: 320 }}>
            Create your free account and get instant spending insights from your first upload.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {["Free to use — no credit card required", "Instant AI categorisation on upload", "Your data stays private and secure"].map((t) => (
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
              Create account
            </h1>
            <p style={{ fontSize: 14, color: "var(--muted)" }}>It takes less than a minute</p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {[
              { label: "Full name",     type: "text",     val: fullName,  set: setFullName,  ph: "Ada Okonkwo"       },
              { label: "Email",         type: "email",    val: email,     set: setEmail,     ph: "you@example.com"   },
              { label: "Password",      type: "password", val: password,  set: setPassword,  ph: "Min. 6 characters" },
            ].map(({ label, type, val, set, ph }) => (
              <div key={label}>
                <label style={{ display: "block", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 8 }}>
                  {label}
                </label>
                <input
                  type={type} required value={val}
                  onChange={(e) => set(e.target.value)}
                  placeholder={ph}
                  className="input-field"
                />
              </div>
            ))}

            {error && <p className="error-box">{error}</p>}

            <button type="submit" disabled={loading} className="btn-primary" style={{ width: "100%", marginTop: 4, padding: "12px" }}>
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p style={{ marginTop: 28, fontSize: 13, color: "var(--muted)" }}>
            Already have an account?{" "}
            <Link href="/login" style={{ color: "var(--ink)", fontWeight: 600, textDecoration: "underline" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>

    </div>
  );
}
