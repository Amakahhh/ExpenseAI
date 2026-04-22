/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void:    "#05050A",
        s1:      "#0D0D1A",
        s2:      "#12121F",
        s3:      "#1A1A2E",
        violet:  "#6C63FF",
        "violet-dim": "#4A43CC",
        cyan:    "#00D4FF",
        warm:    "#FF6B35",
        success: "#00E5A0",
        "text-primary": "#F0F0FF",
        "text-muted":   "#6B6B8A",
      },
      fontFamily: {
        display: ["var(--font-display)", "Bricolage Grotesque", "sans-serif"],
        mono:    ["var(--font-mono)",    "Azeret Mono",         "monospace"],
        body:    ["var(--font-body)",    "DM Sans",             "sans-serif"],
      },
      animation: {
        "breathe":    "breathe 4s ease-in-out infinite",
        "shimmer":    "shimmer 2s linear infinite",
        "slide-up":   "slideUp 0.6s cubic-bezier(0.22,1,0.36,1) both",
        "fade-focus": "fadeFocus 0.55s cubic-bezier(0.22,1,0.36,1) both",
        "float":      "float 6s ease-in-out infinite",
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
        "holo":       "holoShimmer 4s linear infinite",
        "particle":   "particleDrift var(--dur,4s) ease-in-out var(--delay,0s) infinite",
        "draw-edge":  "drawEdge 1.5s ease forwards",
        "ripple":     "ripple 0.8s ease-out forwards",
        "toast-in":   "toastIn 0.4s cubic-bezier(0.22,1,0.36,1) forwards",
        "toast-out":  "toastOut 0.3s ease forwards",
        "stage-in":   "stageReveal 0.45s cubic-bezier(0.22,1,0.36,1) both",
        "progress":   "progressRing 1s ease-out forwards",
        "count-beam": "countBeam 0.5s cubic-bezier(0.22,1,0.36,1) both",
      },
      keyframes: {
        breathe: {
          "0%,100%": { boxShadow: "0 0 20px 2px rgba(140,124,248,0.1), 0 0 60px 10px rgba(140,124,248,0.03), inset 0 0 20px rgba(140,124,248,0.02)" },
          "50%":     { boxShadow: "0 0 40px 8px rgba(140,124,248,0.28), 0 0 100px 24px rgba(140,124,248,0.1), inset 0 0 40px rgba(140,124,248,0.05)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition:  "200% 0" },
        },
        slideUp: {
          "0%":   { opacity: 0, transform: "translateY(20px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        fadeFocus: {
          "0%":   { opacity: 0, filter: "blur(8px)",  transform: "translateY(12px)" },
          "100%": { opacity: 1, filter: "blur(0px)", transform: "translateY(0)"   },
        },
        float: {
          "0%,100%": { transform: "translateY(0px)"  },
          "50%":     { transform: "translateY(-8px)" },
        },
        glowPulse: {
          "0%,100%": { boxShadow: "0 0 10px rgba(0,229,160,0.25)" },
          "50%":     { boxShadow: "0 0 30px rgba(0,229,160,0.65), 0 0 60px rgba(0,229,160,0.25)" },
        },
        holoShimmer: {
          "0%":   { backgroundPosition: "-100% 0" },
          "100%": { backgroundPosition:  "300% 0" },
        },
        particleDrift: {
          "0%":   { transform: "translateY(0) translateX(0) scale(1)",                         opacity: 0 },
          "20%":  { opacity: 0.6 },
          "80%":  { opacity: 0.3 },
          "100%": { transform: "translateY(-130px) translateX(var(--dx,20px)) scale(0.4)", opacity: 0 },
        },
        drawEdge: {
          "to": { strokeDashoffset: 0 },
        },
        ripple: {
          "0%":   { transform: "scale(0)", opacity: 0.6 },
          "100%": { transform: "scale(4)", opacity: 0   },
        },
        toastIn: {
          "0%":   { transform: "translateY(120%) translateX(-50%)", opacity: 0 },
          "100%": { transform: "translateY(0) translateX(-50%)",    opacity: 1 },
        },
        toastOut: {
          "0%":   { transform: "translateY(0) translateX(-50%)",    opacity: 1 },
          "100%": { transform: "translateY(120%) translateX(-50%)", opacity: 0 },
        },
        stageReveal: {
          "0%":   { clipPath: "inset(0 100% 0 0)" },
          "100%": { clipPath: "inset(0 0% 0 0)"   },
        },
        progressRing: {
          "0%":   { strokeDashoffset: 283 },
          "100%": { strokeDashoffset: "var(--target-offset, 0)" },
        },
        countBeam: {
          "0%":   { clipPath: "inset(0 100% 0 0)" },
          "100%": { clipPath: "inset(0 0% 0 0)"   },
        },
      },
    },
  },
  plugins: [],
};
