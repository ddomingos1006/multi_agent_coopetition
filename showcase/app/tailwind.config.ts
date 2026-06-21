import type { Config } from "tailwindcss";
export default {
  darkMode: ["class"], content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      background: "hsl(var(--background))", foreground: "hsl(var(--foreground))",
      card: "hsl(var(--card))", border: "hsl(var(--border))",
      primary: "hsl(var(--primary))", destructive: "hsl(var(--destructive))",
      muted: "hsl(var(--muted))", "muted-foreground": "hsl(var(--muted-foreground))"
    }, borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)" },
    fontFamily: { sans: ["var(--font-sans)"], mono: ["var(--font-mono)"] }
  } }, plugins: []
} satisfies Config;
