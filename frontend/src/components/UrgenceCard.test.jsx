import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UrgenceCard from './UrgenceCard'

describe('UrgenceCard', () => {
  it('affiche le titre', () => {
    render(<UrgenceCard title="SSI Réunion" jours_restants={5} score={80} source="DECP" />)
    expect(screen.getByText('SSI Réunion')).toBeInTheDocument()
  })

  it('affiche J-5', () => {
    render(<UrgenceCard title="Test" jours_restants={5} score={80} source="DECP" />)
    expect(screen.getByText('J-5')).toBeInTheDocument()
  })

  it('affiche badge rouge si jours_restants < 7', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={3} score={80} source="DECP" />)
    expect(container.querySelector('.bg-red-100')).toBeInTheDocument()
  })

  it('affiche badge orange si jours_restants entre 7 et 15', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={10} score={80} source="DECP" />)
    expect(container.querySelector('.bg-orange-100')).toBeInTheDocument()
  })

  it('affiche badge vert si jours_restants entre 16 et 30', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={20} score={80} source="DECP" />)
    expect(container.querySelector('.bg-green-100')).toBeInTheDocument()
  })

  it('affiche le score et la source', () => {
    render(<UrgenceCard title="Test" jours_restants={10} score={78} source="BOAMP" />)
    expect(screen.getByText('78')).toBeInTheDocument()
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
  })
})
