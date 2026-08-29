/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: '#05070A',
        panel: '#0B0F14',
        panelElevated: '#111720',
        border: '#1C2633',
        primary: '#3B82F6',
        accent: '#06B6D4',
        success: '#10B981',
        warning: '#F59E0B',
        critical: '#EF4444',
        slateText: '#9AA7B5',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      boxShadow: {
        soft: '0 12px 32px rgba(16, 24, 40, 0.25)',
      },
      animation: {
        pulseSoft: 'pulse 2.8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
