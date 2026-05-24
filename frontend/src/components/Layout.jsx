import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { loadSavedBrightness } from '../utils/theme'

const PAGE_TITLES = {
  '/': 'Pipeline',
  '/analytics': 'Analytics',
  '/direction': 'Direction',
  '/urgences': 'Urgences',
  '/parametres': 'Paramètres',
  '/guide': 'Guide',
}

export default function Layout() {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'DEF OI'
  const today = new Date().toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric',
  })

  useEffect(() => { loadSavedBrightness() }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-ocean-deep">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="h-[52px] bg-ocean-navy border-b border-ocean-border flex items-center px-6 flex-shrink-0">
          <span className="font-serif text-xl font-bold text-ocean-text">{title}</span>
          <span className="ml-auto font-mono text-xs text-ocean-muted">{today}</span>
        </header>
        <main
          className="flex-1 overflow-auto bg-ocean-deep"
          style={{ filter: 'brightness(var(--app-brightness, 1))' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
