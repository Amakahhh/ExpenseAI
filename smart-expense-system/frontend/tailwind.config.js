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
        ink:     "#111111",
        accent:  "#C07A10",
        green:   "#1E6B45",
        red:     "#B83232",
        muted:   "#777777",
        ghost:   "#AAAAAA",
        border:  "#E0E0E0",
        surface: "#F7F7F7",
        sidebar: "#0F0F0F",
      },
      fontFamily: {
        sans:  ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "'DM Serif Display'", "Georgia", "serif"],
        mono:  ["var(--font-mono)", "'JetBrains Mono'", "monospace"],
      },
      animation: {
        pulse: "pulse 1.6s ease-in-out infinite",
      },
      keyframes: {
        pulse: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0.45" },
        },
      },
    },
  },
  plugins: [],
};
