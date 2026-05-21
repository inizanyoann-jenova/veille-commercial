// frontend/src/components/TenderDetail.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TenderDetail from './TenderDetail'

vi.mock('../hooks/useTenders', () => ({
  useTender: vi.fn(),
  useUpdateStatus: vi.fn(),
  useUpdateSaved: vi.fn(),
}))

import { useTender, useUpdateStatus, useUpdateSaved } from '../hooks/useTenders'

const MOCK_TENDER = {
  id: 'abc1',
  title: 'Marché SSI La Réunion',
  description: 'Travaux SSI détection incendie',
  source: 'DECP',
  deadline: '2026-06-30T00:00:00',
  jours_restants: 40,
  status: 'À qualifier',
  relevance_score: 78,
  gonogo: 'GO',
  adaptive_score: null,
  is_maintenance: false,
  secteur: 'Public',
  type_opportunite: 'Marché Public',
  type_marche: 'Marché Public',
  amount: 150000,
  is_blacklisted: false,
  is_saved: false,
  notes: null,
  tags: [],
  domaine: '🔥 SSI / Détection incendie',
  territoire: 'La Réunion',
  concurrents: '',
  llm_structured: null,
  fiche_data: {
    sm: 45, sg: 30, sk: 6, smaint: 0,
    label_action: '🟢 Planifier la réponse',
    steps: ['Inscrire au planning', 'Télécharger le DCE'],
    atouts: ['✅ Cœur de métier — SSI/CMSI'],
    risques: [],
  },
}

const MOCK_MUTATION = { mutate: vi.fn(), isPending: false }

describe('TenderDetail', () => {
  beforeEach(() => {
    useUpdateStatus.mockReturnValue(MOCK_MUTATION)
    useUpdateSaved.mockReturnValue(MOCK_MUTATION)
  })

  it('ne rend rien si tenderId est null', () => {
    useTender.mockReturnValue({ data: null, isLoading: false, isError: false })
    const { container } = render(<TenderDetail tenderId={null} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('affiche 3 skeletons en état loading', () => {
    useTender.mockReturnValue({ data: null, isLoading: true, isError: false })
    const { container } = render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(3)
  })

  it('affiche le message erreur si isError', () => {
    useTender.mockReturnValue({ data: null, isLoading: false, isError: true })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText(/impossible de charger ce marché/i)).toBeInTheDocument()
  })

  it('affiche le badge 🟢 GO', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText(/🟢 GO/)).toBeInTheDocument()
  })

  it('affiche le titre du marché', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('Marché SSI La Réunion')).toBeInTheDocument()
  })

  it('affiche le label_action du plan d\'action', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('🟢 Planifier la réponse')).toBeInTheDocument()
  })

  it('affiche les étapes du plan d\'action', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('Inscrire au planning')).toBeInTheDocument()
    expect(screen.getByText('Télécharger le DCE')).toBeInTheDocument()
  })

  it('appelle onClose au clic sur le bouton Fermer', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /fermer/i }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('appelle onClose au clic sur l\'overlay', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.click(document.querySelector('[aria-hidden="true"]'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('appelle onClose à la touche Escape', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('affiche le select de qualification', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByRole('combobox', { name: /qualifier/i })).toBeInTheDocument()
  })

  it('affiche le bouton étoile non sauvegardé', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: /sauvegarder/i })).toBeInTheDocument()
  })
})
