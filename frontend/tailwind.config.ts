import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'Helvetica Neue'",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: ["'SF Mono'", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      colors: {
        black: "#000000",
        white: "#FFFFFF",
        border: "#E5E5E5",
        secondary: "#666666",
        surface: "#E5E5E5",
      },
      transitionDuration: {
        DEFAULT: "150ms",
      },
    },
  },
  plugins: [],
};

export default config;
