import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DuplicatePair from './DuplicatePair'

const PAIR = {
  id: 1,
  similarity_score: 0.92,
  tender_a: { id: 'a1', title: 'SSI Réunion A', relevance_score: 80, source: 'BOAMP', deadline: '2026-06-30T00:00:00' },
  tender_b: { id: 'b1', title: 'SSI Réunion B', relevance_score: 65, source: 'DECP', deadline: '2026-06-30T00:00:00' },
}

describe('DuplicatePair', () => {
  it('affiche les titres des deux tenders', () => {
    render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(screen.getByText('SSI Réunion A')).toBeInTheDocument()
    expect(screen.getByText('SSI Réunion B')).toBeInTheDocument()
  })

  it('affiche le score de similarité', () => {
    render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(screen.getByText(/92%/)).toBeInTheDocument()
  })

  it('appelle onResolve avec archiveId=b1 au clic Garder A', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /garder a/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'keep', archiveId: 'b1' })
  })

  it('appelle onResolve avec archiveId=a1 au clic Garder B', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /garder b/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'keep', archiveId: 'a1' })
  })

  it('appelle onResolve avec action=ignore au clic Ignorer', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /ignorer/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'ignore', archiveId: null })
  })

  it('met en évidence tender_a (score plus élevé)', () => {
    const { container } = render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(container.querySelector('.ring-1')).toBeInTheDocument()
  })
})
