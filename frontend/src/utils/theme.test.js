import { describe, it, expect, beforeEach, vi } from 'vitest'
import { hexToRgbString, applyTheme, loadSavedTheme, DEFAULTS, THEME_KEY } from './theme'

describe('hexToRgbString', () => {
  it('convertit un hex sombre en chaîne RGB', () => {
    expect(hexToRgbString('#040d1a')).toBe('4 13 26')
  })

  it('convertit un hex cyan en chaîne RGB', () => {
    expect(hexToRgbString('#00c8ff')).toBe('0 200 255')
  })

  it('convertit un hex coral en chaîne RGB', () => {
    expect(hexToRgbString('#ff6b6b')).toBe('255 107 107')
  })

  it('convertit un hex texte en chaîne RGB', () => {
    expect(hexToRgbString('#ddeeff')).toBe('221 238 255')
  })
})

describe('applyTheme', () => {
  beforeEach(() => {
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  it('applique les 4 variables CSS sur documentElement', () => {
    const colors = { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' }
    applyTheme(colors)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', '4 13 26')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '0 200 255')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-coral', '255 107 107')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-text', '221 238 255')
  })
})

describe('loadSavedTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  it('applique DEFAULTS si rien en localStorage', () => {
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', DEFAULTS.deep)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', DEFAULTS.cyan)
  })

  it('applique les couleurs sauvegardées depuis localStorage', () => {
    const saved = { deep: '10 20 30', cyan: '100 150 200', coral: '200 50 50', text: '240 240 240' }
    localStorage.setItem(THEME_KEY, JSON.stringify(saved))
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', '10 20 30')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '100 150 200')
  })
})
