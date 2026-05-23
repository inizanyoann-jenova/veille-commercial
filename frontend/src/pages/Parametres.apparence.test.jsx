import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Parametres from './Parametres'

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
}))

vi.mock('../utils/theme', () => ({
  THEME_KEY: 'theme-colors',
  DEFAULTS: { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' },
  hexToRgbString: (hex) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `${r} ${g} ${b}`
  },
  applyTheme: vi.fn(),
  loadSavedTheme: vi.fn(),
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
    expect(screen.getByRole('button', { name: /appliquer/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /réinitialiser/i })).toBeInTheDocument()
  })

  it('sauvegarde dans localStorage au clic sur Appliquer', async () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /appliquer/i }))
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
  })
})
