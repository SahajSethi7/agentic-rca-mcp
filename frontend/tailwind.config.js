/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        micro: ['0.625rem', { lineHeight: '0.875rem' }],
        caption: ['0.6875rem', { lineHeight: '0.95rem' }],
        ui: ['0.75rem', { lineHeight: '1rem' }],
        'body-sm': ['0.8125rem', { lineHeight: '1.15rem' }],
        body: ['0.875rem', { lineHeight: '1.35rem' }],
        lead: ['0.9375rem', { lineHeight: '1.45rem' }],
        section: ['1.0625rem', { lineHeight: '1.45rem' }],
        title: ['1.5rem', { lineHeight: '1.9rem' }],
        display: ['1.75rem', { lineHeight: '2.15rem' }],
      },
      colors: {
        att: {
          50: '#eaf8fe',
          100: '#d3f0fc',
          200: '#9fe2f6',
          300: '#58c9ea',
          400: '#00a8e0',
          500: '#009fdb',
          600: '#0073a8',
          700: '#005a8f',
          800: '#003b5c',
          900: '#061a2f',
          black: '#000000',
          white: '#ffffff',
        },
        primary: {
          DEFAULT: '#009fdb',
          hover: '#0073a8',
          selected: '#005a8f',
          tint: '#eaf8fe',
          soft: '#d3f0fc',
        },
        ink: { DEFAULT: '#0b1720', soft: '#3d5265', muted: '#687789' },
        command: { DEFAULT: '#061a2f' },
        warn: {
          50: '#fff8e1',
          100: '#ffecb3',
          500: '#f59e0b',
          700: '#b45309',
        },
        danger: {
          50: '#fef2f2',
          200: '#fecaca',
          500: '#ef4444',
          700: '#b91c1c',
          800: '#991b1b',
        },
        success: {
          50: '#eaf8fe',
          100: '#d3f0fc',
          500: '#009fdb',
          700: '#005a8f',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(6,26,47,.06)',
        hero: '0 1px 2px rgba(6,26,47,.08), 0 22px 48px -26px rgba(0,90,143,.48)',
      },
    },
  },
  plugins: [],
};
