import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Parametres from './Parametres'
import { applyTheme, applyBrightness } from '../utils/theme'

vi.mock('../hooks/useTenders', () => ({
  useCredentials: () => ({ data: [], refetch: vi.fn(), isError: false }),
  useSaveCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useTestCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useAnalyzePending: () => ({ mutate: vi.fn(), isPending: false }),
  useDuplicates: () => ({ data: [], isLoading: false }),
  useDetectDuplicates: () => ({ mutate: vi.fn(), isPending: false }),
  useResolveDuplicate: () => ({ mutate: vi.fn() }),
  useArchiveOld: () => ({ mutate: vi.fn(), isPending: false }),
  useResetDb: () => ({ mutate: vi.fn(), isPending: false }),
  useSaveMistralKey: () => ({ mutate: vi.fn(), isPending: false, isSuccess: false, isError: false, error: null, reset: vi.fn() }),
  useMistralStatus: () => ({ data: undefined }),
}))

vi.mock('../utils/theme', () => ({
  THEME_KEY: 'theme-colors',
  BRIGHTNESS_KEY: 'app-brightness',
  DEFAULTS: { deep: '0 20 65', cyan: '0 87 184', coral: '227 6 19', text: '221 230 255' },
  DEFAULT_BRIGHTNESS: 1.0,
  hexToRgbString: (hex) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `${r} ${g} ${b}`
  },
  applyTheme: vi.fn(),
  loadSavedTheme: vi.fn(),
  applyBrightness: vi.fn(),
  loadSavedBrightness: vi.fn(),
}))

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Parametres — onglet Apparence', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('affiche l\'onglet Apparence dans la liste des onglets', () => {
    render(<Parametres />, { wrapper: Wrapper })
    expect(screen.getByText(/Apparence/i)).toBeInTheDocument()
  })

  it('affiche les 4 sélecteurs de couleur quand l\'onglet est actif', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByText('Fond')).toBeInTheDocument()
    expect(screen.getByText('Couleur principale')).toBeInTheDocument()
    expect(screen.getByText('Alerte')).toBeInTheDocument()
    expect(screen.getByText('Texte')).toBeInTheDocument()
  })

  it('affiche les boutons Appliquer et Réinitialiser', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByRole('button', { name: /sauvegarder/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /réinitialiser/i })).toBeInTheDocument()
  })

  it('sauvegarde les couleurs dans localStorage au clic sur Appliquer', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /sauvegarder/i }))
    const saved = localStorage.getItem('theme-colors')
    expect(saved).not.toBeNull()
    const parsed = JSON.parse(saved)
    expect(parsed).toHaveProperty('deep')
    expect(parsed).toHaveProperty('cyan')
    expect(parsed).toHaveProperty('coral')
    expect(parsed).toHaveProperty('text')
  })

  it('efface localStorage et réinitialise au clic sur Réinitialiser', () => {
    localStorage.setItem('theme-colors', JSON.stringify({ deep: '10 20 30', cyan: '100 100 100', coral: '200 50 50', text: '240 240 240' }))
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser/i }))
    expect(localStorage.getItem('theme-colors')).toBeNull()
    expect(applyTheme).toHaveBeenCalledWith({ deep: '0 20 65', cyan: '0 87 184', coral: '227 6 19', text: '221 230 255' })
  })

  it('affiche le slider de luminosité', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByRole('slider', { name: /luminosité/i })).toBeInTheDocument()
  })

  it('appelle applyBrightness quand le slider change', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    const slider = screen.getByRole('slider', { name: /luminosité/i })
    fireEvent.change(slider, { target: { value: '1.5' } })
    expect(applyBrightness).toHaveBeenCalledWith(1.5)
  })

  it('sauvegarde brightness dans localStorage au clic sur Appliquer', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    const slider = screen.getByRole('slider', { name: /luminosité/i })
    fireEvent.change(slider, { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: /sauvegarder/i }))
    expect(localStorage.getItem('app-brightness')).toBe('1.5')
  })

  it('supprime brightness de localStorage au clic sur Réinitialiser', () => {
    localStorage.setItem('app-brightness', '1.5')
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser/i }))
    expect(localStorage.getItem('app-brightness')).toBeNull()
    expect(applyBrightness).toHaveBeenCalledWith(1.0)
  })

  it('affiche la valeur en % à côté du slider', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByText('100%')).toBeInTheDocument()
  })
})
