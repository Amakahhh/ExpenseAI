"use client";

import { useState, useCallback, useEffect, useRef, DragEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { uploadFile } from "@/lib/api";

const STAGES = [
  { label: "Parsing",       desc: "Reading file structure & detecting columns" },
  { label: "Tokenizing",    desc: "Breaking descriptions into sub-word tokens"  },
  { label: "BERT Encoding", desc: "Generating 384-dimensional embeddings"       },
  { label: "Classifying",   desc: "Few-shot prototypical network matching"      },
  { label: "Graph Lookup",  desc: "Merchant similarity scoring"                 },
  { label: "Complete",      desc: "All transactions analyzed"                   },
];

const STAGE_MS = 1100; // ms per stage

type Phase = "idle" | "dragging" | "processing" | "warming" | "done";

/* Tiny floating particle */
function Particle({ style }: { style: React.CSSProperties }) {
  return <div className="particle" style={style} />;
}

/* Progress ring SVG */
function ProgressRing({ pct }: { pct: number }) {
  const r = 44, c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <svg width="100" height="100" viewBox="0 0 100 100" className="-rotate-90">
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(108,99,255,0.1)" strokeWidth="4" />
      <circle
        cx="50" cy="50" r={r} fill="none"
        stroke="url(#ring-grad)" strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        style={{ transition: "stroke-dashoffset 0.4s ease" }}
      />
      <defs>
        <linearGradient id="ring-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%"   stopColor="#6C63FF" />
          <stop offset="100%" stopColor="#00D4FF" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function FileUpload() {
  const [phase, setPhase]               = useState<Phase>("idle");
  const [isDragging, setIsDragging]     = useState(false);
  const [stageIdx, setStageIdx]         = useState(-1);
  const [processed, setProcessed]       = useState(0);
  const [total, setTotal]               = useState(0);
  const [error, setError]               = useState<string | null>(null);
  const [particles, setParticles]       = useState<React.CSSProperties[]>([]);
  const apiDone   = useRef(false);
  const router    = useRouter();

  // Generate particles once on mount
  useEffect(() => {
    setParticles(
      Array.from({ length: 18 }, () => ({
        left:  `${Math.random() * 100}%`,
        top:   `${60 + Math.random() * 35}%`,
        "--dur":   `${3 + Math.random() * 4}s`,
        "--delay": `${Math.random() * 4}s`,
        "--dx":    `${(Math.random() - 0.5) * 80}px`,
        opacity: 0.4 + Math.random() * 0.3,
      } as React.CSSProperties))
    );
  }, []);

  const runPipeline = useCallback(async (file: File) => {
    setPhase("processing");
    setStageIdx(0);
    setProcessed(0);
    setTotal(0);
    apiDone.current = false;

    // Start API call in parallel
    const apiPromise = uploadFile(file)
      .then((result) => {
        sessionStorage.setItem("session_id", result.session_id);
        sessionStorage.setItem("transaction_count", String(result.total));
        setTotal(result.total);
        apiDone.current = true;
        return result;
      })
      .catch((err: Error) => {
        setError(err.message || "Upload failed — check your file format.");
        setPhase("idle");
        throw err;
      });

    // Advance through stages on a timer
    for (let i = 0; i < STAGES.length - 1; i++) {
      await new Promise((r) => setTimeout(r, STAGE_MS));
      setStageIdx(i + 1);
    }

    // If API is still running after animation, show warming state
    if (!apiDone.current) setPhase("warming");

    // Wait for API if still running
    try {
      const result = await apiPromise;
      // Animate counter
      let n = 0;
      const step = Math.ceil(result.total / 40);
      const counter = setInterval(() => {
        n = Math.min(n + step, result.total);
        setProcessed(n);
        if (n >= result.total) clearInterval(counter);
      }, 30);
    } catch {
      return;
    }

    await new Promise((r) => setTimeout(r, 600));
    setPhase("done");
    await new Promise((r) => setTimeout(r, 500));
    router.push("/dashboard");
  }, [router]);

  const handleFile = useCallback((file: File) => {
    setError(null);
    runPipeline(file);
  }, [runPipeline]);

  const onDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onFileChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const pct = stageIdx < 0 ? 0 : Math.round(((stageIdx + 1) / STAGES.length) * 100);

  /* ── PROCESSING STATE ──────────────────────────────────────────────── */
  if (phase === "processing" || phase === "warming" || phase === "done") {
    return (
      <div className="w-full max-w-md mx-auto animate-fade-focus">
        {/* Progress ring + counter */}
        <div className="flex flex-col items-center mb-10">
          <div className="relative">
            <ProgressRing pct={pct} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-xl font-semibold" style={{ color: "#F0F0FF" }}>
                {pct}%
              </span>
            </div>
          </div>
          {total > 0 && (
            <p className="mt-3 font-mono text-xs" style={{ color: "#6B6B8A" }}>
              Processed{" "}
              <span style={{ color: "#00D4FF" }}>{processed.toLocaleString()}</span>
              {" / "}
              <span style={{ color: "#F0F0FF" }}>{total.toLocaleString()}</span>
              {" transactions"}
            </p>
          )}
        </div>

        {/* Stage pipeline */}
        <div className="relative space-y-0">
          {/* Vertical connector line */}
          <div
            className="absolute left-[19px] top-5 bottom-5 w-px"
            style={{ background: "rgba(108,99,255,0.15)" }}
          />

          {STAGES.map((stage, i) => {
            const done    = i < stageIdx;
            const active  = i === stageIdx;
            const pending = i > stageIdx;

            return (
              <div
                key={stage.label}
                className="relative flex items-start gap-4 py-3 pl-1"
                style={{ opacity: pending ? 0.35 : 1, transition: "opacity 0.4s ease" }}
              >
                {/* Node */}
                <div
                  className="relative z-10 w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
                  style={{
                    background: done
                      ? "rgba(0,229,160,0.15)"
                      : active
                      ? "rgba(108,99,255,0.2)"
                      : "rgba(108,99,255,0.04)",
                    border: done
                      ? "1px solid rgba(0,229,160,0.5)"
                      : active
                      ? "1px solid rgba(108,99,255,0.6)"
                      : "1px solid rgba(108,99,255,0.1)",
                    boxShadow: active ? "0 0 16px rgba(108,99,255,0.35)" : "none",
                  }}
                >
                  {done ? (
                    <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
                      <path d="M3 8l3.5 3.5L13 5" stroke="#00E5A0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : active ? (
                    <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#6C63FF" }} />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full" style={{ background: "rgba(108,99,255,0.3)" }} />
                  )}
                </div>

                {/* Label — clip-path reveal when it becomes active */}
                <div className={`pt-1 ${active ? "animate-stage-in" : ""}`}>
                  <p
                    className="font-display text-sm font-semibold leading-none mb-1"
                    style={{ color: done ? "#00E5A0" : active ? "#F0F0FF" : "#6B6B8A" }}
                  >
                    {stage.label}
                  </p>
                  <p className="text-xs" style={{ color: "#6B6B8A" }}>{stage.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Warming-up notice — shown while waiting for Render cold start */}
        {phase === "warming" && (
          <div
            className="mt-6 flex items-center gap-3 px-4 py-3 rounded-xl text-sm"
            style={{
              background: "rgba(108,99,255,0.08)",
              border: "1px solid rgba(108,99,255,0.2)",
              color: "#6B6B8A",
            }}
          >
            <div className="w-2 h-2 rounded-full shrink-0 animate-pulse" style={{ background: "#6C63FF" }} />
            <span>Server is warming up — this can take up to 60 s on first load…</span>
          </div>
        )}
      </div>
    );
  }

  /* ── IDLE / DRAGGING STATE ─────────────────────────────────────────── */
  return (
    <div className="w-full max-w-xl mx-auto">
      <div
        className={`relative transition-all duration-300 ${isDragging ? "scale-[1.02]" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById("fu")?.click()}
      >
        <input id="fu" type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={onFileChange} />

        {/* Particle field — only visible when dragging */}
        {isDragging && particles.map((s, i) => <Particle key={i} style={s} />)}

        {/* Drop zone */}
        <div
          className="relative cursor-pointer rounded-2xl p-12 flex flex-col items-center gap-5 animate-breathe"
          style={{
            background: isDragging
              ? "rgba(108,99,255,0.08)"
              : "rgba(13,13,26,0.7)",
            border: isDragging
              ? "1.5px solid rgba(108,99,255,0.6)"
              : "1.5px solid rgba(108,99,255,0.2)",
          }}
        >
          {/* Central icon */}
          <div
            className="w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300"
            style={{
              background: "rgba(108,99,255,0.1)",
              border: "1px solid rgba(108,99,255,0.2)",
              boxShadow: isDragging ? "0 0 40px rgba(108,99,255,0.3)" : "none",
            }}
          >
            <svg className="w-9 h-9" viewBox="0 0 36 36" fill="none">
              <path d="M18 4 L18 24" stroke="#6C63FF" strokeWidth="2" strokeLinecap="round" />
              <path d="M11 11 L18 4 L25 11" stroke="#6C63FF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M6 26 L6 30 Q6 32 8 32 L28 32 Q30 32 30 30 L30 26"
                stroke="#00D4FF" strokeWidth="1.5" strokeLinecap="round" />
              <circle cx="28" cy="12" r="6" fill="rgba(0,212,255,0.1)" stroke="#00D4FF" strokeWidth="1" />
              <path d="M25.5 12 L28 14.5 L31 10.5" stroke="#00D4FF" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <div className="text-center space-y-2">
            <p className="font-display text-xl font-semibold" style={{ color: "#F0F0FF" }}>
              {isDragging ? "Release to analyze" : "Drop your bank statement"}
            </p>
            <p className="text-sm" style={{ color: "#6B6B8A" }}>
              or{" "}
              <span className="underline underline-offset-2" style={{ color: "#6C63FF" }}>
                click to browse
              </span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            {["CSV", "XLSX", "XLS"].map((ext) => (
              <span
                key={ext}
                className="px-2.5 py-1 rounded-full font-mono text-xs"
                style={{ background: "rgba(108,99,255,0.1)", color: "#6C63FF", border: "1px solid rgba(108,99,255,0.2)" }}
              >
                {ext}
              </span>
            ))}
          </div>

          <p className="text-xs font-mono" style={{ color: "#6B6B8A" }}>
            Any bank format · columns auto-detected
          </p>

          {/* Corner decorations */}
          {[["top-3 left-3", "border-l border-t"], ["top-3 right-3", "border-r border-t"],
            ["bottom-3 left-3", "border-l border-b"], ["bottom-3 right-3", "border-r border-b"]
          ].map(([pos, borders], i) => (
            <div
              key={i}
              className={`absolute ${pos} w-4 h-4 ${borders}`}
              style={{ borderColor: "rgba(108,99,255,0.3)", borderRadius: "2px" }}
            />
          ))}
        </div>
      </div>

      {error && (
        <div
          className="mt-4 p-4 rounded-xl text-sm flex items-start gap-2"
          style={{ background: "rgba(255,107,53,0.08)", border: "1px solid rgba(255,107,53,0.25)", color: "#FF6B35" }}
        >
          <svg className="w-4 h-4 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
