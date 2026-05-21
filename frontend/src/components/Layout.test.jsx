import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './Layout'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('Layout', () => {
  it('affiche la Sidebar et le contenu de la page courante', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>Contenu Pipeline</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
    expect(screen.getByText('Contenu Pipeline')).toBeInTheDocument()
  })

  it('affiche le titre dans la topbar selon la route', () => {
    render(
      <MemoryRouter initialEntries={['/analytics']}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route path="analytics" element={<div>Analytics content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
      { wrapper: Wrapper }
    )
    expect(screen.getByRole('banner').textContent).toBe('Analytics')
  })
})
