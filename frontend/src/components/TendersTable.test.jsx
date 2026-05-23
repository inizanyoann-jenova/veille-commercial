// frontend/src/components/TendersTable.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TendersTable from './TendersTable'

vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
  useAnalyzeTender: vi.fn(),
}))

import { useTenders, useAnalyzeTender } from '../hooks/useTenders'

const MOCK_TENDERS = [
  {
    id: '1',
    title: 'Marché SSI Réunion',
    domaine: 'SSI / Détection incendie',
    territoire: 'La Réunion',
    deadline: '2026-06-30T00:00:00',
    relevance_score: 75,
    gonogo: 'GO',
    status: 'En cours',
    source: 'DECP',
    llm_analysis: { score_pertinence: 75 },
  },
  {
    id: '2',
    title: 'Vidéosurveillance Mayotte',
    domaine: 'Vidéosurveillance / CCTV',
    territoire: 'Mayotte',
    deadline: null,
    relevance_score: 45,
    gonogo: 'Étudier',
    status: 'À qualifier',
    source: 'AFD',
    llm_analysis: null,
  },
  {
    id: '3',
    title: 'Maintenance alarme',
    domaine: 'Autre',
    territoire: 'Non précisé',
    deadline: '2026-07-15T00:00:00',
    relevance_score: 20,
    gonogo: 'Passer',
    status: 'À qualifier',
    source: 'DECP',
    llm_analysis: null,
  },
]

const DEFAULT_PROPS = {
  status: 'Tous',
  secteur: 'Public',
  searchText: '',
  onStatusChange: vi.fn(),
  onSecteurChange: vi.fn(),
  onSearchChange: vi.fn(),
}

describe('TendersTable', () => {
  beforeEach(() => {
    useAnalyzeTender.mockReturnValue({ mutate: vi.fn() })
  })

  it('affiche le filtre statut avec aria-label', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('combobox', { name: /statut/i })).toBeInTheDocument()
  })

  it('affiche le filtre secteur avec aria-label', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('combobox', { name: /secteur/i })).toBeInTheDocument()
  })

  it('affiche le champ de recherche textuelle', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('textbox', { name: /rechercher/i })).toBeInTheDocument()
  })

  it('affiche un message si aucun marché trouvé', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/aucun marché trouvé/i)).toBeInTheDocument()
  })

  it('affiche un message erreur si isError', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: true })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/impossible de charger les marchés/i)).toBeInTheDocument()
  })

  it('affiche les lignes du tableau avec les titres', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText('Marché SSI Réunion')).toBeInTheDocument()
    expect(screen.getByText('Vidéosurveillance Mayotte')).toBeInTheDocument()
    expect(screen.getByText('Maintenance alarme')).toBeInTheDocument()
  })

  it('affiche le badge 🟢 GO', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🟢 GO/)).toBeInTheDocument()
  })

  it('affiche le badge 🟡 Étudier', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🟡 Étudier/)).toBeInTheDocument()
  })

  it('affiche le badge 🔴 Passer', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🔴 Passer/)).toBeInTheDocument()
  })

  it('filtre par searchText sur le titre', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} searchText="SSI" />)
    expect(screen.getByText('Marché SSI Réunion')).toBeInTheDocument()
    expect(screen.queryByText('Vidéosurveillance Mayotte')).not.toBeInTheDocument()
  })

  it('filtre par searchText sur le domaine', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} searchText="CCTV" />)
    expect(screen.getByText('Vidéosurveillance Mayotte')).toBeInTheDocument()
    expect(screen.queryByText('Marché SSI Réunion')).not.toBeInTheDocument()
  })

  it('affiche — pour une deadline nulle', () => {
    useTenders.mockReturnValue({ data: [MOCK_TENDERS[1]], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('affiche 5 skeletons en état loading', () => {
    useTenders.mockReturnValue({ data: [], isLoading: true, isError: false })
    const { container } = render(<TendersTable {...DEFAULT_PROPS} />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(5)
  })

  it('affiche 0 pour un relevance_score nul', () => {
    const tenderNullScore = { ...MOCK_TENDERS[0], relevance_score: null }
    useTenders.mockReturnValue({ data: [tenderNullScore], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    const scores = screen.getAllByText('0')
    expect(scores.length).toBeGreaterThan(0)
  })

  it('appelle onRowClick avec l\'id du marché au clic sur une ligne', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    const onRowClick = vi.fn()
    render(<TendersTable {...DEFAULT_PROPS} onRowClick={onRowClick} />)
    fireEvent.click(screen.getByText('Marché SSI Réunion'))
    expect(onRowClick).toHaveBeenCalledWith('1')
  })

  it('n\'affiche pas cursor-pointer si onRowClick absent', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    const { container } = render(<TendersTable {...DEFAULT_PROPS} />)
    const rows = container.querySelectorAll('tbody tr')
    rows.forEach((row) => {
      expect(row.className).not.toContain('cursor-pointer')
    })
  })

  it('active la ligne avec la touche Enter quand onRowClick fourni', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    const onRowClick = vi.fn()
    render(<TendersTable {...DEFAULT_PROPS} onRowClick={onRowClick} />)
    const firstRow = screen.getAllByRole('button')[0]
    fireEvent.keyDown(firstRow, { key: 'Enter' })
    expect(onRowClick).toHaveBeenCalledWith('1')
  })

  it('affiche le badge ✓ Analysé pour un tender avec llm_analysis', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/✓ Analysé/)).toBeInTheDocument()
  })

  it('affiche le bouton ▶ Analyser pour un tender sans llm_analysis', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    const buttons = screen.getAllByText(/▶ Analyser/)
    expect(buttons.length).toBe(2)
  })

  it('le clic sur ▶ Analyser ne déclenche pas onRowClick', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    const onRowClick = vi.fn()
    render(<TendersTable {...DEFAULT_PROPS} onRowClick={onRowClick} />)
    const analyzeBtn = screen.getAllByText(/▶ Analyser/)[0]
    fireEvent.click(analyzeBtn)
    expect(onRowClick).not.toHaveBeenCalled()
  })

  it('le bouton ▶ Analyser a un aria-label contenant le titre', () => {
    useTenders.mockReturnValue({ data: [MOCK_TENDERS[1]], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('button', { name: /Vidéosurveillance Mayotte/i })).toBeInTheDocument()
  })
})
