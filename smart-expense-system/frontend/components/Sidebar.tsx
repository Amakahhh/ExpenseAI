"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAuthUser, clearToken } from "@/lib/api";
import { LogoFull } from "@/components/Logo";

const NAV = [
  { href: "/",              label: "Upload"       },
  { href: "/dashboard",    label: "Dashboard"    },
  { href: "/transactions", label: "Transactions" },
  { href: "/analytics",    label: "Analytics"    },
];

export default function Sidebar() {
  const path   = usePathname();
  const router = useRouter();
  const [user,      setUser]      = useState<{ email: string; name: string } | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setUser(getAuthUser());
    const stored = localStorage.getItem("sidebar_collapsed");
    if (stored === "true") setCollapsed(true);
  }, []);

  useEffect(() => {
    document.body.setAttribute("data-sc", collapsed ? "1" : "0");
  }, [collapsed]);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("sidebar_collapsed", String(next));
  }

  return (
    <>
      {/* Toggle button — always anchored to the sidebar edge */}
      <button
        onClick={toggle}
        className="sidebar-toggle"
        title={collapsed ? "Open sidebar" : "Collapse sidebar"}
        aria-label={collapsed ? "Open sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect y="2"   width="14" height="1.5" rx="0.75" fill="currentColor" />
            <rect y="6.25" width="14" height="1.5" rx="0.75" fill="currentColor" />
            <rect y="10.5" width="14" height="1.5" rx="0.75" fill="currentColor" />
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M9 2.5L4.5 7 9 11.5" stroke="currentColor" strokeWidth="1.5"
              strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </button>

      <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`}>
        {/* Logo */}
        <div style={{ padding: "26px 20px 22px", flexShrink: 0 }}>
          <LogoFull size={28} dark />
        </div>

        <div style={{ height: 1, background: "#1E1E1E", flexShrink: 0 }} />

        {/* Nav */}
        <nav style={{ flex: 1, paddingTop: 8, paddingBottom: 8, overflowY: "auto" }}>
          {NAV.map(({ href, label }) => {
            const active = path === href;
            return (
              <Link key={href} href={href} className={`nav-item${active ? " active" : ""}`}>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div style={{ flexShrink: 0 }}>
          <div style={{ height: 1, background: "#1E1E1E" }} />
          <div style={{ padding: "16px 20px 28px" }}>
            {user && (
              <p style={{
                fontSize: 11, color: "#555555", marginBottom: 10,
                overflow: "hidden", textOverflow: "ellipsis",
                whiteSpace: "nowrap", letterSpacing: "0.01em",
              }}>
                {user.name || user.email}
              </p>
            )}
            <button
              onClick={() => { clearToken(); router.push("/login"); }}
              style={{
                fontSize: 12, color: "#555555", background: "none",
                border: "none", cursor: "pointer", padding: 0,
                display: "block", letterSpacing: "0.01em",
                transition: "color 0.12s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#FFFFFF")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#555555")}
            >
              Sign out
            </button>
            <p style={{
              fontSize: 10, color: "#333333", marginTop: 24,
              letterSpacing: "0.06em", textTransform: "uppercase",
            }}>
              v1.0
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
