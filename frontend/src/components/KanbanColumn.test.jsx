import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import KanbanColumn from './KanbanColumn'

const ITEMS = [
  { id: 'a1', title: 'Marché SSI La Réunion', score: 80, jours_restants: 5, amount: 100000 },
  { id: 'a2', title: 'Vidéosurveillance Mayotte', score: 72, jours_restants: 20, amount: null },
  { id: 'a3', title: 'CMSI sans deadline', score: 65, jours_restants: null, amount: 50000 },
]

describe('KanbanColumn', () => {
  it('affiche le titre de la colonne', () => {
    render(<KanbanColumn title="✅ GO" items={ITEMS} />)
    expect(screen.getByText('✅ GO')).toBeInTheDocument()
  })

  it('affiche le nombre de cartes', () => {
    render(<KanbanColumn title="✅ GO" items={ITEMS} />)
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('affiche le titre tronqué à 60 chars', () => {
    const longTitle = 'A'.repeat(70)
    render(<KanbanColumn title="GO" items={[{ id: 'x', title: longTitle, score: 70, jours_restants: 10 }]} />)
    expect(screen.getByText(longTitle.slice(0, 60) + '…')).toBeInTheDocument()
  })

  it('colorie en ocean-coral si jours_restants < 7', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[0]]} />)
    expect(container.querySelector('.text-ocean-coral')).toBeInTheDocument()
  })

  it('colorie en ocean-gold si jours_restants entre 7 et 30', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[1]]} />)
    expect(container.querySelector('.text-ocean-gold')).toBeInTheDocument()
  })

  it('affiche ocean-muted si jours_restants est null', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[2]]} />)
    expect(container.querySelector('.text-ocean-muted')).toBeInTheDocument()
  })

  it('appelle onStatusChange avec le bon statut au clic bouton', () => {
    const onStatusChange = vi.fn()
    render(
      <KanbanColumn
        title="GO"
        items={[ITEMS[0]]}
        actions={[{ label: 'Marquer Soumis', nextStatus: 'Soumis' }]}
        onStatusChange={onStatusChange}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /marquer soumis/i }))
    expect(onStatusChange).toHaveBeenCalledWith('a1', 'Soumis')
  })

  it('affiche un message vide si items est vide', () => {
    render(<KanbanColumn title="GO" items={[]} />)
    expect(screen.getByText(/aucun marché/i)).toBeInTheDocument()
  })
})
