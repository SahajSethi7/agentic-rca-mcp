/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      colors: {
        ink: { DEFAULT: '#17202a', soft: '#4c5a67', muted: '#73808c' },
        command: { DEFAULT: '#10202c', teal: '#0f766e', amber: '#b45309', red: '#b42318' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.06), 0 16px 40px -28px rgba(15,23,42,.35)',
        hero: '0 1px 2px rgba(16,24,40,.08), 0 22px 48px -26px rgba(15,23,42,.45)',
      },
    },
  },
  plugins: [],
};
