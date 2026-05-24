import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UrgenceCard from './UrgenceCard'

const baseProps = {
  title: 'SSI CHU Mayotte',
  jours_restants: 5,
  score: 80,
  source: 'BOAMP',
}

describe('UrgenceCard — base', () => {
  it('affiche le titre', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('SSI CHU Mayotte')).toBeInTheDocument()
  })

  it('affiche J-5', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('J-5')).toBeInTheDocument()
  })

  it('affiche le score', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('80')).toBeInTheDocument()
  })

  it('affiche la source', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
  })
})

describe('UrgenceCard — lien annonce', () => {
  it('affiche le lien si url présente', () => {
    render(<UrgenceCard {...baseProps} url="https://www.boamp.fr/detail/123" />)
    const link = screen.getByRole('link', { name: /annonce/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://www.boamp.fr/detail/123')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('n\'affiche pas de lien si url absente', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.queryByRole('link', { name: /annonce/i })).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — contenu texte', () => {
  it('affiche le résumé LLM si disponible', () => {
    render(<UrgenceCard {...baseProps} llm_resume="Résumé IA du marché" />)
    expect(screen.getByText('Résumé IA du marché')).toBeInTheDocument()
  })

  it('affiche la description en fallback si pas de llm_resume', () => {
    render(<UrgenceCard {...baseProps} description="Description du marché" />)
    expect(screen.getByText('Description du marché')).toBeInTheDocument()
  })

  it('n\'affiche pas de bloc texte si ni llm_resume ni description', () => {
    const { container } = render(<UrgenceCard {...baseProps} />)
    expect(container.querySelector('[data-testid="card-content"]')).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — secteur', () => {
  it('affiche le badge secteur si présent', () => {
    render(<UrgenceCard {...baseProps} secteur="SSI" />)
    expect(screen.getByText('SSI')).toBeInTheDocument()
  })

  it('n\'affiche pas de badge secteur si absent', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.queryByTestId('secteur-badge')).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — montant', () => {
  it('affiche le montant formaté si présent', () => {
    render(<UrgenceCard {...baseProps} amount={45000} />)
    expect(screen.getByText(/45/)).toBeInTheDocument()
  })

  it('n\'affiche pas de montant si absent', () => {
    const { container } = render(<UrgenceCard {...baseProps} />)
    expect(container.querySelector('[data-testid="amount"]')).not.toBeInTheDocument()
  })
})
