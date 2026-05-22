import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { useChartData, useKpisCa } from '../hooks/useTenders'

const COLORS_TERRITOIRE = ['#6366f1', '#e94560', '#f59e0b', '#10b981', '#94a3b8']
const COULEUR_DEF = '#e94560'

function getWeekLabel(date) {
  const d = new Date(date)
  const start = new Date(d.getFullYear(), 0, 1)
  const week = Math.ceil(((d - start) / 86400000 + start.getDay() + 1) / 7)
  return `S${week} ${d.getFullYear()}`
}

function computeCharts(data) {
  const now = new Date()
  const cutoff = new Date(now)
  cutoff.setDate(cutoff.getDate() - 7 * 30)

  // Publications par semaine (30 dernières semaines)
  const weekMap = {}
  data.forEach((d) => {
    if (!d.publication_date) return
    const dt = new Date(d.publication_date)
    if (dt < cutoff) return
    const label = getWeekLabel(dt)
    weekMap[label] = (weekMap[label] || 0) + 1
  })
  const byWeek = Object.entries(weekMap)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([week, count]) => ({ week, count }))

  // Par territoire
  const terMap = {}
  data.forEach((d) => {
    const t = d.territoire || 'Non précisé'
    terMap[t] = (terMap[t] || 0) + 1
  })
  const byTerritoire = Object.entries(terMap)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }))

  // Par domaine
  const domMap = {}
  data.forEach((d) => {
    const parts = (d.domaine || 'Autre').split(', ')
    parts.forEach((p) => { domMap[p] = (domMap[p] || 0) + 1 })
  })
  const byDomaine = Object.entries(domMap)
    .sort((a, b) => b[1] - a[1])
    .map(([domaine, count]) => ({ domaine, count }))

  // Top 5 sources
  const srcMap = {}
  data.forEach((d) => { if (d.source) srcMap[d.source] = (srcMap[d.source] || 0) + 1 })
  const topSources = Object.entries(srcMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([source, count]) => ({ source, count }))

  // KPIs
  const total = data.length
  const sources = new Set(data.map((d) => d.source).filter(Boolean)).size

  return { byWeek, byTerritoire, byDomaine, topSources, total, sources }
}

function KpiCard({ label, value, color }) {
  return (
    <div className={`rounded-lg border p-4 flex flex-col gap-1 ${color}`}>
      <span className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-3xl font-bold">{value}</span>
    </div>
  )
}

export default function Analytics() {
  const { data: chartData = [], isLoading, isError } = useChartData()
  const { data: kpisCa } = useKpisCa()

  if (isLoading) {
    return (
      <div className="p-5 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger les données analytics.</p>
  }

  const { byWeek, byTerritoire, byDomaine, topSources, total, sources } = computeCharts(chartData)
  const caGagne = kpisCa?.gagne ?? 0
  const caFormatted = caGagne >= 1000
    ? `${Math.round(caGagne / 1000)} k€`
    : `${caGagne} €`

  return (
    <div className="p-5 space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total collecté" value={total} color="bg-blue-50 border-blue-200 text-blue-700" />
        <KpiCard label="Sources actives" value={sources} color="bg-indigo-50 border-indigo-200 text-indigo-700" />
        <KpiCard label="CA gagné" value={caFormatted} color="bg-green-50 border-green-200 text-green-700" />
        <KpiCard label="CA pipeline" value={`${Math.round((kpisCa?.pipeline ?? 0) / 1000)} k€`} color="bg-amber-50 border-amber-200 text-amber-700" />
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Publications par semaine */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Publications / semaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byWeek} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="week" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill={COULEUR_DEF} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Donut territoire */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Par territoire</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={byTerritoire}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                dataKey="value"
                nameKey="name"
              >
                {byTerritoire.map((_, i) => (
                  <Cell key={i} fill={COLORS_TERRITOIRE[i % COLORS_TERRITOIRE.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Barres horizontales domaine */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Par domaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              layout="vertical"
              data={byDomaine}
              margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="domaine" tick={{ fontSize: 9 }} width={80} />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 5 sources */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-sm">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Top 5 sources</p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-gray-200">
              <th className="text-left py-1 font-medium">Source</th>
              <th className="text-right py-1 font-medium">Marchés</th>
            </tr>
          </thead>
          <tbody>
            {topSources.map(({ source, count }) => (
              <tr key={source} className="border-b border-gray-50">
                <td className="py-1.5 text-gray-700">{source}</td>
                <td className="py-1.5 text-right font-semibold text-gray-800">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
