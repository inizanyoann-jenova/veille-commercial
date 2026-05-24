export const THEME_KEY = 'theme-colors'

export const DEFAULTS = {
  deep:  '4 13 26',
  cyan:  '0 200 255',
  coral: '255 107 107',
  text:  '221 238 255',
}

export function hexToRgbString(hex) {
  if (typeof hex !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(hex)) return null
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r} ${g} ${b}`
}

export function applyTheme(colors) {
  for (const [key, val] of Object.entries(colors)) {
    if (val !== null && val !== undefined) {
      document.documentElement.style.setProperty(`--color-ocean-${key}`, val)
    }
  }
}

export function loadSavedTheme() {
  let saved = null
  try {
    saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null')
  } catch {
    saved = null
  }
  const colors = saved && typeof saved === 'object' ? { ...DEFAULTS, ...saved } : DEFAULTS
  applyTheme(colors)
}

export const BRIGHTNESS_KEY = 'app-brightness'
export const DEFAULT_BRIGHTNESS = 1.0

export function applyBrightness(value) {
  document.documentElement.style.setProperty('--app-brightness', String(value))
}

export function loadSavedBrightness() {
  const saved = parseFloat(localStorage.getItem(BRIGHTNESS_KEY))
  const value = isNaN(saved) ? DEFAULT_BRIGHTNESS : Math.min(2.0, Math.max(0.5, saved))
  applyBrightness(value)
}
