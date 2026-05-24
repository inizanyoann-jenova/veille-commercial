import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  hexToRgbString, applyTheme, loadSavedTheme, DEFAULTS, THEME_KEY,
  applyBrightness, loadSavedBrightness, BRIGHTNESS_KEY, DEFAULT_BRIGHTNESS,
} from './theme'

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

  it('retourne null pour un hex invalide (3 chiffres)', () => {
    expect(hexToRgbString('#fff')).toBeNull()
  })

  it('retourne null pour une entrée non-string', () => {
    expect(hexToRgbString(undefined)).toBeNull()
    expect(hexToRgbString(null)).toBeNull()
  })

  it('convertit les bornes : #000000 et #ffffff', () => {
    expect(hexToRgbString('#000000')).toBe('0 0 0')
    expect(hexToRgbString('#ffffff')).toBe('255 255 255')
  })
})

describe('applyTheme', () => {
  beforeEach(() => {
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  afterEach(() => vi.restoreAllMocks())

  it('applique les 4 variables CSS sur documentElement', () => {
    const colors = { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' }
    applyTheme(colors)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', '4 13 26')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '0 200 255')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-coral', '255 107 107')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-text', '221 238 255')
  })

  it('ignore les valeurs null dans les couleurs', () => {
    applyTheme({ deep: null, cyan: '0 200 255' })
    expect(document.documentElement.style.setProperty).not.toHaveBeenCalledWith('--color-ocean-deep', expect.anything())
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '0 200 255')
  })
})

describe('loadSavedTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  afterEach(() => vi.restoreAllMocks())

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

  it('fusionne les defaults pour les clés manquantes dans la sauvegarde', () => {
    localStorage.setItem(THEME_KEY, JSON.stringify({ cyan: '50 100 150' }))
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', DEFAULTS.deep)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '50 100 150')
  })

  it('utilise les defaults si localStorage contient du JSON invalide', () => {
    localStorage.setItem(THEME_KEY, 'not-valid-json{{{')
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', DEFAULTS.deep)
  })
})

describe('applyBrightness', () => {
  beforeEach(() => {
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  afterEach(() => vi.restoreAllMocks())

  it('définit --app-brightness sur documentElement', () => {
    applyBrightness(1.5)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1.5')
  })

  it('accepte la valeur minimale 0.5', () => {
    applyBrightness(0.5)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '0.5')
  })

  it('accepte la valeur maximale 2.0', () => {
    applyBrightness(2)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '2')
  })

  it('passe les valeurs hors plage telles quelles (pas de clamping)', () => {
    applyBrightness(5)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '5')
  })
})

describe('loadSavedBrightness', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  afterEach(() => vi.restoreAllMocks())

  it('applique DEFAULT_BRIGHTNESS si rien en localStorage', () => {
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', String(DEFAULT_BRIGHTNESS))
  })

  it('applique la valeur sauvegardée depuis localStorage', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '1.5')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1.5')
  })

  it('clamp à 2 les valeurs trop élevées', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '5')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '2')
  })

  it('clamp à 0.5 les valeurs trop basses', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '0.1')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '0.5')
  })

  it('ignore une valeur non-numérique et utilise le défaut', () => {
    localStorage.setItem(BRIGHTNESS_KEY, 'not-a-number')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1')
  })
})
