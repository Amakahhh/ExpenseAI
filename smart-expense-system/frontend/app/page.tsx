import FileUpload from "@/components/FileUpload";

export default function HomePage() {
  return (
    <main
      className="min-h-screen neural-grid flex flex-col items-center justify-center relative overflow-hidden px-6"
      style={{ background: "#05050A" }}
    >
      {/* Ambient orbs */}
      <div className="orb w-[500px] h-[500px] -top-40 left-1/2 -translate-x-1/2"
        style={{ background: "rgba(108,99,255,0.08)" }} />
      <div className="orb w-[300px] h-[300px] bottom-0 right-0"
        style={{ background: "rgba(0,212,255,0.05)" }} />

      <div className="relative z-10 w-full max-w-2xl animate-fade-focus flex flex-col items-center gap-10">

        {/* Eyebrow */}
        <p
          className="font-mono text-[11px] select-none"
          style={{ color: "rgba(140,124,248,0.5)", letterSpacing: "0.2em" }}
        >
          BERT &nbsp;·&nbsp; FEW-SHOT &nbsp;·&nbsp; GRAPH NETWORKS &nbsp;·&nbsp; NGN NATIVE
        </p>

        {/* Hero */}
        <div className="text-center space-y-4">
          <h1 className="font-display font-bold leading-[1.06] tracking-tight"
            style={{ fontSize: "clamp(2.4rem, 6vw, 4rem)", color: "#F0F0FF" }}>
            Intelligent{" "}
            <span style={{
              background: "linear-gradient(135deg, #6C63FF 0%, #00D4FF 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}>
              expense
            </span>
            {" "}analysis
          </h1>
          <p className="text-base max-w-md mx-auto leading-relaxed" style={{ color: "#6B6B8A" }}>
            Upload any Nigerian bank statement. The AI reads every transaction,
            classifies it, and builds a living spending map — in seconds.
          </p>
        </div>

        {/* Upload widget */}
        <FileUpload />

        {/* Capability strip */}
        <div className="flex items-center gap-8 flex-wrap justify-center">
          {[
            { val: "8",      label: "Categories"        },
            { val: "384",    label: "Embedding dims"    },
            { val: "CSV·XLS",label: "Formats supported" },
            { val: "₦",      label: "Naira-native"      },
          ].map(({ val, label }) => (
            <div key={label} className="text-center">
              <p className="font-mono text-lg font-semibold" style={{ color: "#6C63FF" }}>{val}</p>
              <p className="text-xs mt-0.5" style={{ color: "#6B6B8A" }}>{label}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
