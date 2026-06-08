/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#001441',
        accent:  '#E30613',
        ocean: {
          deep:   'rgb(var(--color-ocean-deep) / <alpha-value>)',
          navy:   '#00082A',
          panel:  '#000C36',
          border: 'rgba(0,87,184,0.12)',
          glow:   'rgba(0,87,184,0.20)',
          cyan:   'rgb(var(--color-ocean-cyan) / <alpha-value>)',
          teal:   '#4A90D9',
          coral:  'rgb(var(--color-ocean-coral) / <alpha-value>)',
          gold:   '#ffd700',
          text:   'rgb(var(--color-ocean-text) / <alpha-value>)',
          muted:  'rgba(140,175,230,0.45)',
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
