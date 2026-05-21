import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import KpiGrid from './KpiGrid'

vi.mock('../hooks/useTenders', () => ({
  useKpisPublic: vi.fn(),
}))

import { useKpisPublic } from '../hooks/useTenders'

describe('KpiGrid', () => {
  it('affiche 5 skeletons en état loading', () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: true, isError: false })
    const { container } = render(<KpiGrid />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(5)
  })

  it("affiche un message d'erreur si isError", () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: false, isError: true })
    render(<KpiGrid />)
    expect(screen.getByText(/impossible de charger les kpis/i)).toBeInTheDocument()
  })

  it('affiche les 5 compteurs KPI avec les bonnes valeurs', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 42, a_qualifier: 10, en_cours: 5, soumis: 3, gagnes: 2 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('affiche les labels des 5 cartes', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 0, a_qualifier: 0, en_cours: 0, soumis: 0, gagnes: 0 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText(/total marchés/i)).toBeInTheDocument()
    expect(screen.getByText(/à qualifier/i)).toBeInTheDocument()
    expect(screen.getByText(/en cours/i)).toBeInTheDocument()
    expect(screen.getByText(/soumis/i)).toBeInTheDocument()
    expect(screen.getByText(/gagnés/i)).toBeInTheDocument()
  })
})
