"use client";
import { useState, useMemo, useCallback, useEffect } from "react";
import { Transaction, correctTransaction } from "@/lib/api";

const CATEGORIES = ["food","transport","entertainment","bills","health","education","shopping","utilities","savings","other"] as const;

function catClass(cat: string): string {
  const c = cat?.toLowerCase().trim() ?? "";
  if (c.includes("food") || c.includes("grocery") || c.includes("restaurant") || c.includes("eat")) return "cat-food";
  if (c.includes("transport") || c.includes("uber") || c.includes("bolt") || c.includes("taxi")) return "cat-transport";
  if (c.includes("entertain") || c.includes("movie") || c.includes("game") || c.includes("sport")) return "cat-entertainment";
  if (c.includes("bill") || c.includes("rent") || c.includes("loan") || c.includes("mortgage")) return "cat-bills";
  if (c.includes("health") || c.includes("medical") || c.includes("pharma") || c.includes("hospital")) return "cat-health";
  if (c.includes("edu") || c.includes("school") || c.includes("tuition") || c.includes("course")) return "cat-education";
  if (c.includes("shop") || c.includes("mall") || c.includes("store") || c.includes("cloth")) return "cat-shopping";
  if (c.includes("util") || c.includes("electric") || c.includes("water") || c.includes("airtime") || c.includes("data") || c.includes("mtn") || c.includes("glo") || c.includes("airtel")) return "cat-utilities";
  if (c.includes("sav") || c.includes("invest")) return "cat-savings";
  if (c.includes("income") || c.includes("salary") || c.includes("credit")) return "cat-income";
  return "cat-other";
}

function Toast({ msg, onDone }: { msg: string; onDone: () => void }) {
  useEffect(() => { const t = setTimeout(onDone, 2500); return () => clearTimeout(t); }, [onDone]);
  return (
    <div className="toast">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M2 7l3.5 3.5L12 4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {msg}
    </div>
  );
}

function CorrectionPanel({ tx, onCorrect, onClose }: { tx: Transaction; onCorrect: (c: string) => void; onClose: () => void }) {
  const current = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
  const [selected, setSelected] = useState(current);

  return (
    <tr className="row-expanded-bg">
      <td colSpan={5} style={{ padding: "16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, flex: 1 }}>
            {CATEGORIES.map((c) => (
              <button key={c} onClick={() => setSelected(c)} className={`cat-chip${selected === c ? " selected" : ""}`}>
                {c}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <button className="btn-ghost" style={{ fontSize: 13 }} onClick={onClose}>Cancel</button>
            <button className="btn-primary" style={{ fontSize: 13 }} onClick={() => onCorrect(selected)}>
              Save correction
            </button>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function TransactionTable({ transactions: initial }: { transactions: Transaction[] }) {
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
      setRows((prev) => prev.map((t) => t.id === tx.id ? { ...t, is_corrected: true, corrected_category: newCat } : t));
      setToast("Correction saved");
    } catch { } finally { setCorrecting(null); }
  }, []);

  const expCount = rows.filter((t) => t.transaction_type !== "credit").length;
  const incCount = rows.filter((t) => t.transaction_type === "credit").length;

  return (
    <div>
      {toast && <Toast msg={toast} onDone={() => setToast(null)} />}

      {/* Filter bar */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap", alignItems: "center" }}>
        {/* Search */}
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <svg style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--ghost)", pointerEvents: "none" }}
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          <input type="text" placeholder="Search transactions" value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-field" style={{ paddingLeft: 36 }} />
        </div>

        {/* Category */}
        <select value={catFilter} onChange={(e) => setCatFilter(e.target.value)}
          className="input-field" style={{ width: "auto" }}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
        </select>

        {/* Type toggle */}
        <div style={{ display: "flex", border: "1px solid var(--border)", borderRadius: 3, overflow: "hidden", background: "#FFFFFF" }}>
          {[
            { val: "" as const,       label: `All (${rows.length})` },
            { val: "debit" as const,  label: `Expenses (${expCount})` },
            { val: "credit" as const, label: `Income (${incCount})` },
          ].map(({ val, label }) => (
            <button key={val} onClick={() => setTypeFilter(val)}
              style={{
                padding: "9px 16px", fontSize: 12, fontWeight: 500,
                border: "none", borderLeft: val !== "" ? "1px solid var(--border)" : "none",
                cursor: "pointer",
                background: typeFilter === val ? "var(--ink)" : "#FFFFFF",
                color: typeFilter === val ? "#FFFFFF" : "var(--muted)",
                transition: "background 0.12s, color 0.12s",
                letterSpacing: "0.01em",
              }}
            >{label}</button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="table-shell">
        <table className="data-table">
          <thead>
            <tr>
              {["Date", "Description", "Category", "Type", "Amount"].map((h) => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: "48px 16px", textAlign: "center", color: "var(--ghost)", fontSize: 13 }}>
                  No transactions match your filter.
                </td>
              </tr>
            ) : filtered.map((tx) => {
              const cat = tx.is_corrected ? tx.corrected_category! : tx.predicted_category;
              const isIncome = tx.transaction_type === "credit";
              const isExp = expanded === tx.id;

              return (
                <>
                  <tr key={tx.id} onClick={() => !correcting && setExpanded(isExp ? null : tx.id)}
                    style={{ cursor: "pointer", background: isExp ? "var(--surface)" : undefined }}>

                    <td className="mono" style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>
                      {tx.date}
                    </td>
                    <td style={{ maxWidth: 340 }}>
                      <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 13 }}>
                        {tx.description}
                      </div>
                      {tx.is_corrected && (
                        <span style={{ fontSize: 10, color: "var(--green)", display: "block", marginTop: 2, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>Corrected</span>
                      )}
                    </td>
                    <td><span className={`cat-badge ${catClass(cat)}`}>{cat}</span></td>
                    <td style={{ fontSize: 12, color: "var(--muted)", textTransform: "capitalize" }}>
                      {isIncome ? "credit" : "debit"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: isIncome ? "var(--green)" : "var(--ink)" }}>
                        {isIncome ? "+" : ""}₦{(tx.amount || 0).toLocaleString("en-NG", { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                  </tr>

                  {isExp && (
                    <CorrectionPanel tx={tx} onCorrect={(c) => handleCorrect(tx, c)} onClose={() => setExpanded(null)} />
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 11, color: "var(--ghost)", marginTop: 10, textAlign: "right", fontFamily: "var(--font-mono, monospace)" }}>
        {filtered.length} of {rows.length}
      </p>
    </div>
  );
}
