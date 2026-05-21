import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

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

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="h-11 bg-white border-b border-gray-200 flex items-center px-5 flex-shrink-0">
          <span className="text-sm font-bold text-gray-900">{title}</span>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
