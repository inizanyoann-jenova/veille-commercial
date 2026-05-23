/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#16213e',
        accent: '#e94560',
        ocean: {
          deep:   '#040d1a',
          navy:   '#071428',
          panel:  '#0a1c35',
          border: 'rgba(0,200,255,0.08)',
          glow:   'rgba(0,200,255,0.15)',
          cyan:   '#00c8ff',
          teal:   '#00e5c0',
          coral:  '#ff6b6b',
          gold:   '#ffd700',
          text:   '#ddeeff',
          muted:  'rgba(150,200,240,0.4)',
        },
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans:  ['DM Sans', 'system-ui', 'sans-serif'],
        mono:  ['DM Mono', 'Inconsolata', 'monospace'],
      },
    },
  },
  plugins: [],
}
