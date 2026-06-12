"use client";
import { useState, useCallback, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { uploadFile, saveStoredSession, setActiveSessionId } from "@/lib/api";

type Phase = "idle" | "dragging" | "uploading" | "done";

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M12 3v14M7 8l5-5 5 5" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 18v1a2 2 0 002 2h14a2 2 0 002-2v-1" stroke="var(--muted)" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default function FileUpload() {
  const [phase,    setPhase]    = useState<Phase>("idle");
  const [error,    setError]    = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [filename, setFilename] = useState("");
  const router   = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const runUpload = useCallback(async (file: File) => {
    setError(null);
    setFilename(file.name);
    setPhase("uploading");
    setProgress(0);

    const ticker = setInterval(() => {
      setProgress((p) => p < 82 ? p + Math.random() * 5 : p);
    }, 350);

    try {
      const result = await uploadFile(file);
      clearInterval(ticker);
      setProgress(100);
      sessionStorage.setItem("session_id", result.session_id);
      setActiveSessionId(result.session_id);
      saveStoredSession({
        session_id: result.session_id,
        filename: file.name,
        upload_date: new Date().toISOString(),
        total_transactions: result.total,
        total_spend: result.transactions
          .filter((t) => t.transaction_type === "debit")
          .reduce((s, t) => s + (t.amount || 0), 0),
      });
      setPhase("done");
      await new Promise((r) => setTimeout(r, 700));
      router.push("/dashboard");
    } catch (err: any) {
      clearInterval(ticker);
      setError(err.message || "Upload failed. Please check your file format.");
      setPhase("idle");
    }
  }, [router]);

  const onDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setPhase("idle");
    const file = e.dataTransfer.files[0];
    if (file) runUpload(file);
  }, [runUpload]);

  const onChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) runUpload(file);
  }, [runUpload]);

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

  return (
    <>
      <div
        className={`drop-zone${phase === "dragging" ? " dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setPhase("dragging"); }}
        onDragLeave={() => setPhase("idle")}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" style={{ display: "none" }} onChange={onChange} />
        <UploadIcon />
        <div>
          <p style={{ fontSize: 14, fontWeight: 600, color: "var(--ink)", marginBottom: 4 }}>
            Drop your statement here
          </p>
          <p style={{ fontSize: 12, color: "var(--muted)" }}>
            CSV, XLSX, or XLS
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
