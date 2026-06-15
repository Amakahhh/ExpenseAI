"use client";
import { useState, useCallback, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { uploadFile, saveStoredSession, setActiveSessionId } from "@/lib/api";

type Phase = "idle" | "dragging" | "pdf_ready" | "uploading" | "done";

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M12 3v14M7 8l5-5 5 5" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 18v1a2 2 0 002 2h14a2 2 0 002-2v-1" stroke="var(--muted)" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M9 13h1.5a1 1 0 010 2H9v-4h1.5a1 1 0 010 2" stroke="var(--accent)" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M14 11h1a2 2 0 010 4h-1v-4z" stroke="var(--accent)" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

export default function FileUpload() {
  const [phase,       setPhase]       = useState<Phase>("idle");
  const [error,       setError]       = useState<string | null>(null);
  const [progress,    setProgress]    = useState(0);
  const [filename,    setFilename]    = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pdfPassword, setPdfPassword] = useState("");
  const [pwError,     setPwError]     = useState<string | null>(null);

  const router   = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  // Run the actual upload — called either directly (CSV/Excel) or after password entry (PDF)
  const runUpload = useCallback(async (file: File, password?: string) => {
    setError(null);
    setPwError(null);
    setFilename(file.name);
    setPhase("uploading");
    setProgress(0);

    const ticker = setInterval(() => {
      setProgress((p) => (p < 82 ? p + Math.random() * 5 : p));
    }, 350);

    try {
      const result = await uploadFile(file, password);
      clearInterval(ticker);
      setProgress(100);
      sessionStorage.setItem("session_id", result.session_id);
      setActiveSessionId(result.session_id);
      saveStoredSession({
        session_id:         result.session_id,
        filename:           file.name,
        upload_date:        new Date().toISOString(),
        total_transactions: result.total,
        total_spend:        result.transactions
          .filter((t) => t.transaction_type === "debit")
          .reduce((s, t) => s + (t.amount || 0), 0),
      });
      setPhase("done");
      await new Promise((r) => setTimeout(r, 700));
      router.push("/dashboard");
    } catch (err: any) {
      clearInterval(ticker);
      const msg: string = err.message || "";

      // Backend explicitly says password is needed or wrong
      if (msg === "PDF_NEEDS_PASSWORD" || msg.toLowerCase().includes("password")) {
        setPwError("Incorrect password. Please try again.");
        setPhase("pdf_ready");
        return;
      }

      setError(msg || "Upload failed. Please check your file.");
      setPhase("idle");
    }
  }, [router]);

  // Called when any file is chosen — PDFs get a pre-upload password screen
  const handleFile = useCallback((file: File) => {
    setError(null);
    setPwError(null);
    setPdfPassword("");
    setFilename(file.name);
    setPendingFile(file);

    if (file.name.toLowerCase().endsWith(".pdf")) {
      setPhase("pdf_ready");   // show password field first
    } else {
      runUpload(file);         // CSV/Excel: upload immediately
    }
  }, [runUpload]);

  const onDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setPhase("idle");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }, [handleFile]);

  // ── PDF password screen ───────────────────────────────────────────────────
  if (phase === "pdf_ready") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {/* File badge */}
        <div style={{
          display: "flex", alignItems: "center", gap: 12,
          padding: "12px 14px",
          background: "rgba(192,122,16,0.07)",
          border: "1px solid rgba(192,122,16,0.2)",
          borderRadius: 10,
        }}>
          <PdfIcon />
          <div style={{ minWidth: 0 }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {filename}
            </p>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>PDF selected</p>
          </div>
        </div>

        {/* Password field */}
        <div>
          <label style={{
            display: "block", fontSize: 11, fontWeight: 700,
            letterSpacing: "0.08em", textTransform: "uppercase",
            color: "var(--muted)", marginBottom: 8,
          }}>
            Password <span style={{ fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(leave blank if not protected)</span>
          </label>
          <input
            type="password"
            autoFocus
            placeholder="Enter PDF password"
            value={pdfPassword}
            onChange={(e) => { setPwError(null); setPdfPassword(e.target.value); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && pendingFile) runUpload(pendingFile, pdfPassword || undefined);
            }}
            className="input-field"
          />
          {pwError && (
            <p className="error-box" style={{ marginTop: 8 }}>{pwError}</p>
          )}
        </div>

        {/* Actions */}
        <button
          className="btn-primary"
          style={{ width: "100%" }}
          onClick={() => pendingFile && runUpload(pendingFile, pdfPassword || undefined)}
        >
          Upload Statement
        </button>
        <button
          className="btn-ghost"
          style={{ width: "100%", fontSize: 12 }}
          onClick={() => { setPhase("idle"); setPendingFile(null); setPdfPassword(""); setPwError(null); setFilename(""); }}
        >
          Choose a different file
        </button>
      </div>
    );
  }

  // ── Uploading / done ──────────────────────────────────────────────────────
  if (phase === "uploading" || phase === "done") {
    return (
      <div style={{ padding: "12px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>
            {phase === "done" ? "Analysis complete" : `Analysing ${filename}`}
          </p>
          <span style={{ fontSize: 11, color: "var(--ghost)", fontFamily: "var(--font-mono, monospace)" }}>
            {Math.round(progress)}%
          </span>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <p style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
          {phase === "done" ? "Redirecting to your dashboard…" : "Reading and classifying transactions…"}
        </p>
      </div>
    );
  }

  // ── Idle / drag ───────────────────────────────────────────────────────────
  return (
    <>
      <div
        className={`drop-zone${phase === "dragging" ? " dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setPhase("dragging"); }}
        onDragLeave={() => setPhase("idle")}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          style={{ display: "none" }}
          onChange={onChange}
        />
        <UploadIcon />
        <div>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
            Drop your statement here
          </p>
          <p style={{ fontSize: 12, color: "var(--muted)" }}>
            CSV, XLSX, XLS, or PDF
          </p>
        </div>
      </div>

      <button
        className="btn-primary"
        style={{ width: "100%", marginTop: 12 }}
        onClick={() => inputRef.current?.click()}
      >
        Choose file
      </button>

      {error && <p className="error-box" style={{ marginTop: 12 }}>{error}</p>}
    </>
  );
}
