export const THEME_KEY = 'theme-colors'

export const DEFAULTS = {
  deep:  '4 13 26',
  cyan:  '0 200 255',
  coral: '255 107 107',
  text:  '221 238 255',
}

export function hexToRgbString(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r} ${g} ${b}`
}

export function applyTheme(colors) {
  for (const [key, val] of Object.entries(colors)) {
    document.documentElement.style.setProperty(`--color-ocean-${key}`, val)
  }
}

export function loadSavedTheme() {
  const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null')
  applyTheme(saved ?? DEFAULTS)
}
