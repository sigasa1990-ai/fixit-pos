import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pos: {
          primary: "#2563eb",
          secondary: "#1e40af",
          accent: "#f59e0b",
          success: "#10b981",
          danger: "#ef4444",
          background: "#f8fafc",
          surface: "#ffffff",
          "surface-hover": "#f1f5f9",
          border: "#e2e8f0",
          text: "#0f172a",
          "text-secondary": "#64748b",
        },
      },
      fontSize: {
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
      },
    },
  },
  plugins: [],
}
export default config
