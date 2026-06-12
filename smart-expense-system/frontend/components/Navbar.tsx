"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAuthUser, clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard",    label: "Dashboard"    },
  { href: "/transactions", label: "Transactions" },
  { href: "/analytics",    label: "Analytics"    },
];

export default function Navbar() {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ email: string; name: string } | null>(null);

  useEffect(() => {
    setUser(getAuthUser());
  }, [path]);

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav
      className="sticky top-0 z-50 border-b"
      style={{
        background: "rgba(5,5,10,0.85)",
        borderColor: "rgba(108,99,255,0.12)",
        backdropFilter: "blur(12px)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-8 h-8">
            <svg viewBox="0 0 32 32" fill="none" className="w-8 h-8">
              <rect width="32" height="32" rx="8" fill="rgba(108,99,255,0.15)" stroke="rgba(108,99,255,0.4)" strokeWidth="1" />
              <circle cx="16" cy="16" r="5" fill="none" stroke="#6C63FF" strokeWidth="1.5" />
              <circle cx="16" cy="16" r="1.5" fill="#6C63FF" />
              <line x1="16" y1="4"  x2="16" y2="9"  stroke="#6C63FF" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="16" y1="23" x2="16" y2="28" stroke="#6C63FF" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="4"  y1="16" x2="9"  y2="16" stroke="#00D4FF" strokeWidth="1.5" strokeLinecap="round" />
              <line x1="23" y1="16" x2="28" y2="16" stroke="#00D4FF" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
              style={{ boxShadow: "0 0 16px rgba(108,99,255,0.5)" }} />
          </div>
          <span className="font-display font-semibold text-base tracking-tight" style={{ color: "#F0F0FF" }}>
            Expense<span style={{ color: "#6C63FF" }}>IQ</span>
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {NAV.map(({ href, label }) => {
            const active = path === href;
            return (
              <Link
                key={href}
                href={href}
                className="relative px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200"
                style={{
                  color: active ? "#F0F0FF" : "#6B6B8A",
                  background: active ? "rgba(108,99,255,0.15)" : "transparent",
                }}
              >
                {label}
                {active && (
                  <span
                    className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full"
                    style={{ background: "#6C63FF" }}
                  />
                )}
              </Link>
            );
          })}
        </div>

        {/* User + logout */}
        <div className="flex items-center gap-3">
          {user && (
            <span className="text-xs font-mono hidden sm:block" style={{ color: "#6B6B8A" }}>
              {user.name || user.email}
            </span>
          )}
          {user ? (
            <button
              onClick={handleLogout}
              className="text-xs font-mono px-3 py-1.5 rounded-lg border transition-all duration-200 hover:border-red-500/40 hover:text-red-400"
              style={{ color: "#6B6B8A", borderColor: "rgba(108,99,255,0.2)" }}
            >
              Sign out
            </button>
          ) : (
            <Link
              href="/login"
              className="text-xs font-mono px-3 py-1.5 rounded-lg border transition-all"
              style={{ color: "#6C63FF", borderColor: "rgba(108,99,255,0.3)" }}
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
