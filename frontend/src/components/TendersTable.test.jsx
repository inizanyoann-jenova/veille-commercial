import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TendersTable from './TendersTable'

vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
  useAnalyzeTender: vi.fn(() => ({ mutate: vi.fn() })),
}))

import { useTenders } from '../hooks/useTenders'

const makeTenders = (n, offset = 0) =>
  Array.from({ length: n }, (_, i) => ({
    id: `T${offset + i}`,
    title: `Marché ${offset + i}`,
    relevance_score: 50,
    status: 'À qualifier',
    source: 'test',
    gonogo: 'GO',
    domaine: 'SSI',
    territoire: 'La Réunion',
    publication_date: '2026-01-01',
    deadline: null,
    llm_analysis: null,
    url: null,
    is_maintenance: false,
  }))

const defaultProps = {
  status: 'Tous',
  secteur: 'Public',
  searchText: '',
  gonogo: 'Tous',
  onStatusChange: vi.fn(),
  onSecteurChange: vi.fn(),
  onSearchChange: vi.fn(),
  onGonogoChange: vi.fn(),
  onRowClick: vi.fn(),
}

describe('TendersTable — pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le bouton "Charger 200 de plus" si la page a exactement 200 résultats', () => {
    useTenders.mockReturnValue({
      data: makeTenders(200),
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.getByRole('button', { name: /Charger 200 de plus/i })).toBeDefined()
  })

  it("n'affiche pas le bouton si la page a moins de 200 résultats", () => {
    useTenders.mockReturnValue({
      data: makeTenders(42),
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.queryByRole('button', { name: /Charger 200 de plus/i })).toBeNull()
  })

  it("n'affiche pas le bouton si la page est vide", () => {
    useTenders.mockReturnValue({
      data: [],
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.queryByRole('button', { name: /Charger 200 de plus/i })).toBeNull()
  })
})
