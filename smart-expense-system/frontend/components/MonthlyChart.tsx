"use client";

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { MonthlyStat } from "@/lib/api";

interface Props { data: MonthlyStat[] }

const fmt  = (v: number) => `₦${(v / 1000).toFixed(0)}k`;
const fmtT = (v: number) => `₦${v.toLocaleString("en-NG", { minimumFractionDigits: 2 })}`;

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0D0D1A", border: "1px solid rgba(108,99,255,0.25)",
      borderRadius: 10, padding: "10px 14px",
    }}>
      <p style={{ color: "#6B6B8A", fontSize: 11, marginBottom: 4, fontFamily: "var(--font-mono)" }}>{label}</p>
      <p style={{ color: "#6C63FF", fontSize: 15, fontFamily: "var(--font-mono)", fontWeight: 600 }}>
        {fmtT(payload[0].value)}
      </p>
    </div>
  );
};

export default function MonthlyChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="violet-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#6C63FF" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#6C63FF" stopOpacity={0}    />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(108,99,255,0.06)" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fill: "#6B6B8A", fontSize: 11, fontFamily: "var(--font-mono)" }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fill: "#6B6B8A", fontSize: 11, fontFamily: "var(--font-mono)" }}
          axisLine={false} tickLine={false} width={44}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(108,99,255,0.2)", strokeWidth: 1 }} />
        <Area
          type="monotone"
          dataKey="total"
          stroke="#6C63FF"
          strokeWidth={2}
          fill="url(#violet-grad)"
          className="chart-glow-line"
          dot={false}
          activeDot={{ r: 4, fill: "#6C63FF", stroke: "#F0F0FF", strokeWidth: 1.5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
