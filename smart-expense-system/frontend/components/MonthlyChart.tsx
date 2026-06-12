"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { MonthlyStat } from "@/lib/api";

const fmt  = (v: number) => `₦${(v / 1000).toFixed(0)}k`;
const fmtT = (v: number) => `₦${v.toLocaleString("en-NG", { minimumFractionDigits: 2 })}`;

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#FFFFFF", border: "1px solid #E0E0E0", borderRadius: 3, padding: "10px 14px" }}>
      <p style={{ fontSize: 11, color: "#777777", marginBottom: 4 }}>{label}</p>
      <p style={{ fontSize: 14, fontWeight: 600, color: "#111111", fontFamily: "var(--font-mono, monospace)" }}>
        {fmtT(payload[0].value)}
      </p>
    </div>
  );
}

export default function MonthlyChart({ data }: { data: MonthlyStat[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#F0F0F0" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: "#AAAAAA", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmt} tick={{ fill: "#AAAAAA", fontSize: 11 }} axisLine={false} tickLine={false} width={44} />
        <Tooltip content={<Tip />} cursor={{ stroke: "#E0E0E0", strokeWidth: 1 }} />
        <Line
          type="monotone" dataKey="total"
          stroke="#111111" strokeWidth={1.5}
          dot={false}
          activeDot={{ r: 3, fill: "#111111", stroke: "#FFFFFF", strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
