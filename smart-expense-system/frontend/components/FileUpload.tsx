"use client";
import { useState, useCallback, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { uploadFile, saveStoredSession, setActiveSessionId, PDFPasswordError } from "@/lib/api";

type Phase = "idle" | "dragging" | "uploading" | "needs_password" | "done";

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M12 3v14M7 8l5-5 5 5" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 18v1a2 2 0 002 2h14a2 2 0 002-2v-1" stroke="var(--muted)" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="11" width="18" height="11" rx="2" stroke="var(--accent)" strokeWidth="1.6" />
      <path d="M7 11V7a5 5 0 0110 0v4" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="16" r="1.5" fill="var(--accent)" />
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
      if (err instanceof PDFPasswordError) {
        // PDF is password-protected — store file and ask for password
        setPendingFile(file);
        setPdfPassword("");
        setPhase("needs_password");
      } else if (phase === "needs_password" || password !== undefined) {
        // Wrong password was entered
        setPwError("Incorrect password. Please try again.");
        setPhase("needs_password");
      } else {
        setError(err.message || "Upload failed. Please check your file.");
        setPhase("idle");
      }
    }
  }, [router, phase]);

  const onDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setPhase("idle");
    const file = e.dataTransfer.files[0];
    if (file) runUpload(file);
  }, [runUpload]);

  const onChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) runUpload(file);
    // Reset input so the same file can be re-selected if needed
    e.target.value = "";
  }, [runUpload]);

  // ── Password prompt ────────────────────────────────────────────────────────
  if (phase === "needs_password") {
    return (
      <div style={{ padding: "8px 0" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, marginBottom: 20 }}>
          <LockIcon />
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
              Password-protected PDF
            </p>
            <p style={{ fontSize: 12, color: "var(--muted)" }}>
              Enter the password your bank set for this statement.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <input
            type="password"
            autoFocus
            placeholder="Statement password"
            value={pdfPassword}
            onChange={(e) => { setPwError(null); setPdfPassword(e.target.value); }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && pendingFile) runUpload(pendingFile, pdfPassword);
            }}
            className="input-field"
          />

          {pwError && <p className="error-box">{pwError}</p>}

          <button
            className="btn-primary"
            style={{ width: "100%" }}
            disabled={!pdfPassword.trim()}
            onClick={() => pendingFile && runUpload(pendingFile, pdfPassword)}
          >
            Unlock &amp; Upload
          </button>

          <button
            className="btn-ghost"
            style={{ width: "100%", fontSize: 12 }}
            onClick={() => { setPhase("idle"); setPendingFile(null); setPdfPassword(""); setPwError(null); }}
          >
            Cancel — choose a different file
          </button>
        </div>
      </div>
    );
  }

  // ── Upload progress ────────────────────────────────────────────────────────
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

  // ── Idle / drag ────────────────────────────────────────────────────────────
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
