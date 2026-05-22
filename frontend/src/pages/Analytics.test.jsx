// frontend/src/pages/Analytics.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Analytics from './Analytics'

vi.mock('../hooks/useTenders', () => ({
  useChartData: vi.fn(),
  useKpisCa: vi.fn(),
}))

import { useChartData, useKpisCa } from '../hooks/useTenders'

describe('Analytics', () => {
  it('affiche les squelettes animate-pulse en état de chargement', () => {
    useChartData.mockReturnValue({ data: [], isLoading: true, isError: false })
    useKpisCa.mockReturnValue({ data: undefined })

    const { container } = render(<Analytics />)
    const pulses = container.querySelectorAll('.animate-pulse')
    expect(pulses.length).toBeGreaterThan(0)
  })

  it('affiche le message d\'erreur en état d\'erreur', () => {
    useChartData.mockReturnValue({ data: [], isLoading: false, isError: true })
    useKpisCa.mockReturnValue({ data: undefined })

    render(<Analytics />)
    expect(
      screen.getByText('Impossible de charger les données analytics.')
    ).toBeInTheDocument()
  })
})
