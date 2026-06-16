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
        ink: { DEFAULT: '#1e2330', soft: '#475067' },
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,40,.05), 0 4px 16px -10px rgba(31,38,95,.18)',
        hero: '0 1px 2px rgba(16,24,40,.05), 0 12px 32px -14px rgba(31,38,95,.28)',
      },
    },
  },
  plugins: [],
};
