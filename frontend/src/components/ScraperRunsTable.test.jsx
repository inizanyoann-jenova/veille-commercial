import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScraperRunsTable from './ScraperRunsTable'

vi.mock('../hooks/useTenders', () => ({
  useScraperRuns: vi.fn(),
}))
import { useScraperRuns } from '../hooks/useTenders'

const MOCK_RUNS = [
  { id: 1, source_name: 'BOAMP', started_at: '2026-05-21T10:00:00', finished_at: '2026-05-21T10:01:00', nb_found: 12, nb_new: 3, status: 'ok', error: null },
  { id: 2, source_name: 'DECP', started_at: '2026-05-21T10:01:00', finished_at: null, nb_found: null, nb_new: null, status: 'error', error: 'Timeout' },
]

describe('ScraperRunsTable', () => {
  it('affiche un message vide si aucun run', () => {
    useScraperRuns.mockReturnValue({ data: [], isLoading: false })
    render(<ScraperRunsTable />)
    expect(screen.getByText(/aucun historique/i)).toBeInTheDocument()
  })

  it('affiche le nom de la source', () => {
    useScraperRuns.mockReturnValue({ data: MOCK_RUNS, isLoading: false })
    render(<ScraperRunsTable />)
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
    expect(screen.getByText('DECP')).toBeInTheDocument()
  })

  it('affiche le statut ok en ocean-teal', () => {
    useScraperRuns.mockReturnValue({ data: [MOCK_RUNS[0]], isLoading: false })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelector('.text-ocean-teal')).toBeInTheDocument()
  })

  it('affiche le statut error en ocean-coral', () => {
    useScraperRuns.mockReturnValue({ data: [MOCK_RUNS[1]], isLoading: false })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelector('.text-ocean-coral')).toBeInTheDocument()
  })

  it('affiche les skeletons en chargement', () => {
    useScraperRuns.mockReturnValue({ data: [], isLoading: true })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})
