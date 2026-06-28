import type { Config } from "tailwindcss";

/**
 * Token-basiertes Theme. Alle Farben referenzieren CSS-Variablen aus
 * `src/index.css` (`:root` hell, `[data-theme="dark"]` dunkel), damit der
 * Dark-Mode rein über das `data-theme`-Attribut umschaltet.
 */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        numeric: ["Space Grotesk", "ui-monospace", "monospace"],
      },
      colors: {
        // surfaces
        bg: "var(--bg)",
        app: "var(--app)",
        surface: "var(--surface)",
        surface2: "var(--surface2)",
        // borders
        border: "var(--border)",
        border2: "var(--border2)",
        // text
        ink: "var(--ink)",
        ink2: "var(--ink2)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        // brand
        brand: "var(--brand)",
        brand2: "var(--brand2)",
        brandsoft: "var(--brandsoft)",
        brandink: "var(--brandink)",
        // semantic status
        okbg: "var(--okbg)",
        oktext: "var(--oktext)",
        warnbg: "var(--warnbg)",
        warntext: "var(--warntext)",
        dangerbg: "var(--dangerbg)",
        dangertext: "var(--dangertext)",
        infobg: "var(--infobg)",
        infotext: "var(--infotext)",
        inquirybg: "var(--inquirybg)",
        inquirytext: "var(--inquirytext)",
        whatsapp: "var(--whatsapp)",
        // sidebar rail
        rail1: "var(--rail1)",
        rail2: "var(--rail2)",
        railtext: "var(--railtext)",
        railfaint: "var(--railfaint)",
      },
      boxShadow: {
        card: "var(--shadow)",
        "card-lg": "var(--shadowlg)",
        glow: "0 10px 22px -8px rgba(99,102,241,.55)",
      },
      borderRadius: {
        lg: "0.6875rem", // 11px innere Felder
        xl: "0.75rem", // 12px Buttons
        "2xl": "1rem", // 16px Karten
      },
      backgroundImage: {
        "rail-gradient": "linear-gradient(180deg, var(--rail1), var(--rail2))",
        "brand-gradient": "linear-gradient(120deg, #6366f1, #7c3aed)",
        "brand-gradient-140": "linear-gradient(140deg, #6366f1, #7c3aed)",
      },
      animation: {
        "fade-up": "fadeUp 0.35s ease both",
        "slide-from-right": "slideFromRight 0.4s cubic-bezier(.2,.8,.2,1) both",
        "pop-in": "popIn 0.3s cubic-bezier(.2,.8,.2,1) both",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
        spring: "cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
