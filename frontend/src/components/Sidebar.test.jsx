import { vi } from 'vitest'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './Sidebar'

vi.mock('../hooks/useTenders', () => ({
  useUrgences: vi.fn(() => ({ data: [] })),
  useSources: vi.fn(() => ({ data: [] })),
  useCredentials: vi.fn(() => ({ data: [] })),
  useCollectMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    data: {
      status: 'ok',
      results: [
        { source: 'DECP', status: 'ok', nb_new: 5 },
        { source: 'AFD', status: 'ok', nb_new: 3 },
      ],
    },
    reset: vi.fn(),
  })),
  useAnalyzePending: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Sidebar', () => {
  it('affiche le logo ATEXIA', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('ATEXIA')).toBeInTheDocument()
  })

  it('affiche tous les items de navigation', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('Pipeline')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Direction')).toBeInTheDocument()
    expect(screen.getByText('Urgences')).toBeInTheDocument()
    expect(screen.getByText('Guide')).toBeInTheDocument()
    expect(screen.getByText('Paramètres')).toBeInTheDocument()
  })
})

describe('Sidebar — résultats post-collecte', () => {
  it('affiche le total de nouvelles offres après collecte', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('+8 nouvelles offres')).toBeInTheDocument()
  })

  it("n'affiche pas les barres Collecte et Mots-clés", () => {
    render(<Sidebar />, { wrapper: Wrapper })
    // The StepBar labels render in <span class="text-[9px] text-ocean-muted">
    // The section header "Collecte" is in a <p> with uppercase class — we target only spans
    const spans = document.querySelectorAll('span.text-\\[9px\\].text-ocean-muted')
    const spanTexts = Array.from(spans).map((s) => s.textContent.toLowerCase())
    expect(spanTexts).not.toContain('collecte')
    expect(spanTexts).not.toContain('mots-clés')
    expect(screen.queryByText(/mots-clés/i)).not.toBeInTheDocument()
  })

  it('affiche la barre Analyse IA', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText(/analyse ia/i)).toBeInTheDocument()
  })
})
