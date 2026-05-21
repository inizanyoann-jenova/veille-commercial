import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './Sidebar'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Sidebar', () => {
  it('affiche le logo DEF OI', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
  })

  it('affiche tous les items de navigation', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('Pipeline')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Direction')).toBeInTheDocument()
    expect(screen.getByText('Urgences')).toBeInTheDocument()
    expect(screen.getByText('Guide')).toBeInTheDocument()
    expect(screen.getByText('Paramètres')).toBeInTheDocument()
  })
})
