// frontend/src/pages/Dashboard.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Dashboard from './Dashboard'

vi.mock('../components/KpiGrid', () => ({
  default: () => <div data-testid="kpi-grid">KpiGrid</div>,
}))

vi.mock('../components/TendersTable', () => ({
  default: (props) => (
    <div data-testid="tenders-table">
      <span data-testid="prop-status">{props.status}</span>
      <span data-testid="prop-secteur">{props.secteur}</span>
      <span data-testid="prop-search">{props.searchText}</span>
      <button onClick={() => props.onStatusChange('En cours')}>set-status</button>
      <button onClick={() => props.onSecteurChange('Privé')}>set-secteur</button>
      <button onClick={() => props.onSearchChange('test')}>set-search</button>
      <button onClick={() => props.onRowClick?.('t-1')}>row-click</button>
    </div>
  ),
}))

vi.mock('../components/TenderDetail', () => ({
  default: (props) =>
    props.tenderId
      ? <div data-testid="tender-detail" data-tender-id={props.tenderId} />
      : null,
}))

describe('Dashboard', () => {
  it('rend KpiGrid et TendersTable', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('kpi-grid')).toBeInTheDocument()
    expect(screen.getByTestId('tenders-table')).toBeInTheDocument()
  })

  it('initialise status à "Tous"', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-status').textContent).toBe('Tous')
  })

  it('initialise secteur à "Public"', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-secteur').textContent).toBe('Public')
  })

  it('initialise searchText à ""', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-search').textContent).toBe('')
  })

  it('met à jour status via onStatusChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-status'))
    expect(screen.getByTestId('prop-status').textContent).toBe('En cours')
  })

  it('met à jour secteur via onSecteurChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-secteur'))
    expect(screen.getByTestId('prop-secteur').textContent).toBe('Privé')
  })

  it('met à jour searchText via onSearchChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-search'))
    expect(screen.getByTestId('prop-search').textContent).toBe('test')
  })

  it('TenderDetail n\'est pas rendu initialement', () => {
    render(<Dashboard />)
    expect(screen.queryByTestId('tender-detail')).not.toBeInTheDocument()
  })

  it('ouvre TenderDetail avec le bon tenderId au clic sur une ligne', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('row-click'))
    const detail = screen.getByTestId('tender-detail')
    expect(detail).toBeInTheDocument()
    expect(detail.dataset.tenderId).toBe('t-1')
  })
})
