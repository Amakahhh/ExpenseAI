import Link from "next/link";

function LogoMark({ size = 28, dark = false }: { size?: number; dark?: boolean }) {
  const bar = dark ? "#FFFFFF" : "#111111";
  const dot  = "#C07A10";
  return (
    <svg width={size * 0.8} height={size * 0.8} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3"  y="16" width="4" height="5" rx="0.5" fill={bar} />
      <rect x="10" y="10" width="4" height="11" rx="0.5" fill={bar} />
      <rect x="17" y="5"  width="4" height="16" rx="0.5" fill={bar} />
      <circle cx="5" cy="10" r="2.5" fill={dot} />
    </svg>
  );
}

export function LogoFull({ size = 28, href = "/", dark = false }: { size?: number; href?: string; dark?: boolean }) {
  const textColor = dark ? "#FFFFFF" : "#111111";
  const content = (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 9, textDecoration: "none" }}>
      <LogoMark size={size} dark={dark} />
      <span style={{
        fontSize: size * 0.54,
        fontWeight: 700,
        color: textColor,
        letterSpacing: "-0.01em",
        fontFamily: "var(--font-inter, Inter, sans-serif)",
      }}>
        Expense<span style={{ color: "#C07A10" }}>AI</span>
      </span>
    </span>
  );
  return <Link href={href} style={{ textDecoration: "none" }}>{content}</Link>;
}

export function LogoMarkOnly({ size = 28, dark = false }: { size?: number; dark?: boolean }) {
  return <LogoMark size={size} dark={dark} />;
}
