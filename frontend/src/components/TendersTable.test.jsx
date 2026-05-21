// frontend/src/components/TendersTable.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TendersTable from './TendersTable'

vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
}))

import { useTenders } from '../hooks/useTenders'

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
})
