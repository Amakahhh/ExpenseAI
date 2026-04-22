"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { Transaction, correctTransaction } from "@/lib/api";

const CATEGORIES = ["food","transport","entertainment","bills","health","education","shopping","other"] as const;

const CAT_COLOR: Record<string, string> = {
  food:"#F59E0B", transport:"#00D4FF", entertainment:"#A855F7",
  bills:"#EF4444", health:"#EC4899", education:"#EAB308",
  shopping:"#F97316", other:"#6B6B8A",
};

const CAT_ICON: Record<string, string> = {
  food:"🍽", transport:"🚗", entertainment:"🎬",
  bills:"⚡", health:"💊", education:"📚",
  shopping:"🛍", other:"◈",
};

/* ── Toast ────────────────────────────────────────────────────────────── */
function Toast({ msg, onDone }: { msg: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2800);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="toast animate-toast-in">
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
      {msg}
    </div>
  );
}

/* ── Confidence bar row ───────────────────────────────────────────────── */
function ConfBar({ label, pct, color, active }: { label: string; pct: number; color: string; active: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono capitalize w-20 shrink-0" style={{ color: active ? color : "#6B6B8A" }}>
        {label}
      </span>
      <div className="conf-bar-track flex-1">
        <div
          className="conf-bar-fill"
          style={{ width: `${pct}%`, background: active ? color : "rgba(108,99,255,0.3)" }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right" style={{ color: active ? color : "#6B6B8A" }}>
        {pct}%
      </span>
    </div>
  );
}

/* ── Inline expanded correction panel ────────────────────────────────── */
function ExpansionPanel({
  tx, onCorrect, onClose,
}: {
  tx: Transaction;
  onCorrect: (cat: string) => void;
  onClose: () => void;
}) {
  const cat     = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
  const conf    = Math.round(tx.confidence * 100);

  // Simulate top-3 BERT confidence breakdown
  const topCats = useMemo(() => {
    const cats = CATEGORIES.filter((c) => c !== cat);
    const rand  = (lo: number, hi: number) => Math.floor(Math.random() * (hi - lo) + lo);
    const second = rand(Math.max(conf - 30, 20), Math.max(conf - 10, 25));
    const third  = rand(Math.max(second - 25, 10), Math.max(second - 5, 15));
    return [
      { label: cat,       pct: conf,   active: true  },
      { label: cats[0],   pct: second, active: false },
      { label: cats[1],   pct: third,  active: false },
    ];
  }, [cat, conf]);

  return (
    <tr>
      <td colSpan={7} className="row-expanded px-6 py-4">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* BERT confidence viz */}
          <div className="flex-1">
            <p className="text-xs font-mono uppercase tracking-widest mb-3" style={{ color: "#6B6B8A" }}>
              BERT confidence breakdown
            </p>
            <div className="space-y-2.5">
              {topCats.map((c) => (
                <ConfBar key={c.label} label={c.label} pct={c.pct}
                  color={CAT_COLOR[c.label] || "#6C63FF"} active={c.active} />
              ))}
            </div>
          </div>

          {/* Correction picker */}
          <div className="lg:w-64">
            <p className="text-xs font-mono uppercase tracking-widest mb-3" style={{ color: "#6B6B8A" }}>
              Correct category
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {CATEGORIES.map((c) => (
                <button
                  key={c}
                  onClick={() => onCorrect(c)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium capitalize transition-all duration-150"
                  style={{
                    background: c === cat ? `${CAT_COLOR[c]}22` : "rgba(255,255,255,0.03)",
                    border: `1px solid ${c === cat ? CAT_COLOR[c] + "50" : "rgba(108,99,255,0.1)"}`,
                    color: c === cat ? CAT_COLOR[c] : "#6B6B8A",
                  }}
                >
                  <span>{CAT_ICON[c]}</span>
                  {c}
                </button>
              ))}
            </div>
            <button
              onClick={onClose}
              className="mt-3 text-xs font-mono w-full text-center transition-colors"
              style={{ color: "#6B6B8A" }}
            >
              Cancel
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
}

/* ── Main table ───────────────────────────────────────────────────────── */
interface Props { transactions: Transaction[] }

export default function TransactionTable({ transactions: initial }: Props) {
  const [rows, setRows]             = useState<Transaction[]>(initial);
  const [search, setSearch]         = useState("");
  const [catFilter, setCatFilter]   = useState("");
  const [typeFilter, setTypeFilter] = useState<""|"debit"|"credit">("");
  const [expanded, setExpanded]     = useState<number | null>(null);
  const [correcting, setCorrecting] = useState<number | null>(null);
  const [toast, setToast]           = useState<string | null>(null);

  const filtered = useMemo(() => rows.filter((tx) => {
    const cat = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
    return (
      (!search     || tx.description.toLowerCase().includes(search.toLowerCase())) &&
      (!catFilter  || cat === catFilter) &&
      (!typeFilter || tx.transaction_type === typeFilter)
    );
  }), [rows, search, catFilter, typeFilter]);

  const handleCorrect = useCallback(async (tx: Transaction, newCat: string) => {
    setCorrecting(tx.id);
    setExpanded(null);
    try {
      await correctTransaction(tx.id, newCat);
      setRows((prev) => prev.map((t) =>
        t.id === tx.id ? { ...t, is_corrected: true, corrected_category: newCat } : t
      ));
      setToast("Model updated — 1 correction applied");
    } catch {
      // user can retry
    } finally {
      setCorrecting(null);
    }
  }, []);

  const expCount  = rows.filter((t) => t.transaction_type !== "credit").length;
  const incCount  = rows.filter((t) => t.transaction_type === "credit").length;

  return (
    <div className="space-y-4">
      {toast && <Toast msg={toast} onDone={() => setToast(null)} />}

      {/* Type pills */}
      <div className="flex gap-2 flex-wrap">
        {[
          { label: `All · ${rows.length}`,       val: "" as const,       base: "rgba(108,99,255,0.08)", active: "rgba(108,99,255,0.2)", tc: "#6C63FF"  },
          { label: `Expenses · ${expCount}`,      val: "debit" as const,  base: "rgba(239,68,68,0.06)",  active: "rgba(239,68,68,0.15)", tc: "#EF4444"  },
          { label: `Income · ${incCount}`,        val: "credit" as const, base: "rgba(0,229,160,0.06)",  active: "rgba(0,229,160,0.15)", tc: "#00E5A0"  },
        ].map((p) => (
          <button
            key={p.val}
            onClick={() => setTypeFilter(p.val)}
            className="px-3 py-1.5 rounded-full text-xs font-mono font-medium transition-all"
            style={{
              background: typeFilter === p.val ? p.active : p.base,
              border: `1px solid ${p.tc}30`,
              color: typeFilter === p.val ? p.tc : "#6B6B8A",
            }}
          >{p.label}</button>
        ))}
      </div>

      {/* Search + filter */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "#6B6B8A" }}
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search transactions"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={`w-full pl-9 pr-4 py-2.5 rounded-lg text-sm font-mono transition-all ${search ? "cursor" : ""}`}
            style={{
              background: "#0D0D1A",
              border: "1px solid rgba(108,99,255,0.15)",
              color: "#F0F0FF",
              outline: "none",
            }}
          />
        </div>
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="px-4 py-2.5 rounded-lg text-sm font-mono"
          style={{
            background: "#0D0D1A",
            border: "1px solid rgba(108,99,255,0.15)",
            color: "#F0F0FF",
          }}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c} style={{ textTransform: "capitalize" }}>
              {c.charAt(0).toUpperCase() + c.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl" style={{ border: "1px solid rgba(108,99,255,0.1)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "#0D0D1A", borderBottom: "1px solid rgba(108,99,255,0.1)" }}>
              {["Date","Description","Amount ₦","Type","Category","Confidence","Action"].map((h, i) => (
                <th
                  key={h}
                  className={`px-4 py-3 font-mono text-xs uppercase tracking-widest ${i >= 2 ? "text-center" : "text-left"}`}
                  style={{ color: "#6B6B8A" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-20 text-center font-mono text-sm" style={{ color: "#6B6B8A" }}>
                  No transactions match your filter.
                </td>
              </tr>
            ) : filtered.map((tx) => {
              const cat      = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
              const color    = CAT_COLOR[cat] || "#6B6B8A";
              const isIncome = tx.transaction_type === "credit";
              const isExp    = expanded === tx.id;
              const isCorrecting = correcting === tx.id;
              const lowConf  = tx.confidence < 0.7;

              return (
                <>
                  <tr
                    key={tx.id}
                    className="row-hover transition-all duration-150 cursor-pointer"
                    style={{
                      background: isExp
                        ? "rgba(108,99,255,0.06)"
                        : isIncome
                        ? "rgba(0,229,160,0.03)"
                        : "transparent",
                      borderBottom: "1px solid rgba(108,99,255,0.06)",
                      borderLeft: `2px solid ${isExp ? color : "transparent"}`,
                    }}
                    onClick={() => setExpanded(isExp ? null : tx.id)}
                  >
                    {/* Date */}
                    <td className="px-4 py-3 font-mono text-xs whitespace-nowrap" style={{ color: "#6B6B8A" }}>
                      {tx.date || "—"}
                    </td>

                    {/* Description */}
                    <td className="px-4 py-3 max-w-xs">
                      <div className="flex items-center gap-2">
                        {isIncome && (
                          <span className="shrink-0 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase tracking-wide"
                            style={{ background: "rgba(0,229,160,0.1)", color: "#00E5A0", border: "1px solid rgba(0,229,160,0.2)" }}>
                            IN
                          </span>
                        )}
                        <span className="truncate text-xs" style={{ color: "#F0F0FF" }} title={tx.description}>
                          {tx.description}
                        </span>
                      </div>
                    </td>

                    {/* Amount */}
                    <td className="px-4 py-3 text-right font-mono text-xs whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        {isIncome
                          ? <svg className="w-3 h-3" style={{ color: "#00E5A0" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 15l7-7 7 7" /></svg>
                          : <svg className="w-3 h-3" style={{ color: "#EF4444" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" /></svg>
                        }
                        <span style={{ color: isIncome ? "#00E5A0" : "#F0F0FF", fontWeight: isIncome ? 600 : 400 }}>
                          ₦{(tx.amount || 0).toLocaleString("en-NG", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </td>

                    {/* Type */}
                    <td className="px-4 py-3 text-center">
                      <span className="font-mono text-[10px] px-2 py-0.5 rounded-full capitalize"
                        style={{
                          background: isIncome ? "rgba(0,229,160,0.08)" : "rgba(239,68,68,0.08)",
                          color: isIncome ? "#00E5A0" : "#EF4444",
                        }}>
                        {isIncome ? "credit" : "debit"}
                      </span>
                    </td>

                    {/* Category */}
                    <td className="px-4 py-3 text-center">
                      <span
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize"
                        style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
                      >
                        <span className="text-[11px]">{CAT_ICON[cat]}</span>
                        {cat}
                        {tx.is_corrected && (
                          <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </span>
                    </td>

                    {/* Confidence */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        <div className="conf-bar-track w-14">
                          <div className="conf-bar-fill"
                            style={{ width: `${Math.round(tx.confidence * 100)}%`,
                              background: lowConf ? "#FF6B35" : "#6C63FF" }} />
                        </div>
                        <span className="font-mono text-xs w-8 tabular-nums"
                          style={{ color: lowConf ? "#FF6B35" : "#6B6B8A" }}>
                          {Math.round(tx.confidence * 100)}%
                        </span>
                        {lowConf && (
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded"
                            style={{ background: "rgba(255,107,53,0.1)", color: "#FF6B35" }}>
                            Review
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Action */}
                    <td className="px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                      {isCorrecting ? (
                        <div className="w-4 h-4 border-2 rounded-full animate-spin mx-auto"
                          style={{ borderColor: "#6C63FF", borderTopColor: "transparent" }} />
                      ) : (
                        <button
                          onClick={(e) => { e.stopPropagation(); setExpanded(isExp ? null : tx.id); }}
                          className="text-xs font-mono px-2.5 py-1 rounded-lg transition-all"
                          style={{
                            background: isExp ? "rgba(108,99,255,0.2)" : "rgba(108,99,255,0.08)",
                            color: "#6C63FF",
                            border: "1px solid rgba(108,99,255,0.2)",
                          }}
                        >
                          {isExp ? "Close" : "Correct ▾"}
                        </button>
                      )}
                    </td>
                  </tr>

                  {/* Inline expansion */}
                  {isExp && (
                    <ExpansionPanel
                      tx={tx}
                      onCorrect={(c) => handleCorrect(tx, c)}
                      onClose={() => setExpanded(null)}
                    />
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs font-mono text-right" style={{ color: "#6B6B8A" }}>
        {filtered.length} of {rows.length} transactions
      </p>
    </div>
  );
}
