import { NavLink } from 'react-router-dom'
import { useUrgences } from '../hooks/useTenders'

const NAV_ITEMS = [
  { to: '/', icon: '📋', label: 'Pipeline', end: true },
  { to: '/analytics', icon: '📊', label: 'Analytics' },
  { to: '/direction', icon: '🎯', label: 'Direction' },
  { to: '/urgences', icon: '🔔', label: 'Urgences', badge: true },
  { to: '/guide', icon: '📖', label: 'Guide' },
]

function NavItem({ to, icon, label, badge, urgenceCount, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 py-2 text-sm transition-colors',
          isActive
            ? 'bg-red-500/15 border-l-[3px] border-red-500 pl-[13px] text-white font-semibold'
            : 'pl-[17px] text-[#5a6e8a] hover:text-white',
        ].join(' ')
      }
    >
      <span className="text-base leading-none">{icon}</span>
      <span>{label}</span>
      {badge && urgenceCount > 0 && (
        <span className="ml-auto mr-3 bg-red-500 text-white text-[10px] font-bold rounded-full px-1.5 py-px">
          {urgenceCount}
        </span>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { data: urgences = [] } = useUrgences()

  return (
    <aside className="w-52 bg-[#16213e] flex flex-col flex-shrink-0 h-screen">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-white/[0.07]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-red-500 rounded-lg flex items-center justify-center text-white font-extrabold text-xs flex-shrink-0">
            OI
          </div>
          <div>
            <p className="text-white text-[10px] font-bold leading-tight">DEF Océan Indien</p>
            <p className="text-[#4a5a72] text-[9px] mt-0.5">Veille Marchés</p>
          </div>
        </div>
      </div>

      {/* Navigation principale */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} urgenceCount={urgences.length} />
        ))}
      </nav>

      {/* Paramètres épinglés en bas */}
      <div className="border-t border-white/[0.07] py-2">
        <NavItem to="/parametres" icon="⚙️" label="Paramètres" />
      </div>
    </aside>
  )
}
