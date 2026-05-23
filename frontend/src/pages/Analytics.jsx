import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { useChartData, useKpisCa } from '../hooks/useTenders'

const COLORS_TERRITOIRE = ['#00c8ff', '#00e5c0', '#ff6b6b', '#ffd700', 'rgba(150,200,240,0.4)']
const COULEUR_DEF = '#00c8ff'

function getWeekLabel(date) {
  const d = new Date(date)
  const start = new Date(d.getFullYear(), 0, 1)
  const week = String(Math.ceil(((d - start) / 86400000 + start.getDay() + 1) / 7)).padStart(2, '0')
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

function KpiCard({ label, value, topColor }) {
  return (
    <div className={`bg-ocean-panel border border-ocean-border rounded-xl p-5 flex flex-col gap-1 border-t-2 ${topColor}`}>
      <span className="font-sans text-xs uppercase tracking-widest text-ocean-muted">{label}</span>
      <span className="font-serif text-4xl font-bold text-ocean-text">{value}</span>
    </div>
  )
}

export default function Analytics() {
  const { data: chartData = [], isLoading, isError } = useChartData()
  const { data: kpisCa } = useKpisCa()

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-ocean-panel/50 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 rounded-xl bg-ocean-panel/50 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return <p className="p-6 text-ocean-coral text-sm">Impossible de charger les données analytics.</p>
  }

  const { byWeek, byTerritoire, byDomaine, topSources, total, sources } = computeCharts(chartData)
  const caGagne = kpisCa?.gagne ?? 0
  const caFormatted = caGagne >= 1000
    ? `${Math.round(caGagne / 1000)} k€`
    : `${caGagne} €`
  const caPipeline = kpisCa?.pipeline ?? 0
  const pipelineFormatted = caPipeline >= 1000
    ? `${Math.round(caPipeline / 1000)} k€`
    : `${caPipeline} €`

  return (
    <div className="p-6 space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total collecté" value={total} topColor="border-ocean-cyan" />
        <KpiCard label="Sources actives" value={sources} topColor="border-ocean-teal" />
        <KpiCard label="CA gagné" value={caFormatted} topColor="border-ocean-gold" />
        <KpiCard label="CA pipeline" value={pipelineFormatted} topColor="border-ocean-coral" />
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Publications par semaine */}
        <div className="bg-ocean-panel border border-ocean-border rounded-xl p-4">
          <p className="font-mono text-xs text-ocean-muted uppercase tracking-widest mb-3">Publications / semaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byWeek} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="week" tick={{ fontSize: 9, fill: 'rgba(150,200,240,0.4)' }} interval="preserveStartEnd" axisLine={{ stroke: 'rgba(0,200,255,0.1)' }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'rgba(150,200,240,0.4)' }} axisLine={{ stroke: 'rgba(0,200,255,0.1)' }} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#0a1c35', border: '1px solid rgba(0,200,255,0.08)', borderRadius: '8px', color: '#ddeeff', fontSize: '12px' }} />
              <Bar dataKey="count" fill={COULEUR_DEF} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Donut territoire */}
        <div className="bg-ocean-panel border border-ocean-border rounded-xl p-4">
          <p className="font-mono text-xs text-ocean-muted uppercase tracking-widest mb-3">Par territoire</p>
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
                {byTerritoire.map(({ name }, i) => (
                  <Cell key={name} fill={COLORS_TERRITOIRE[i % COLORS_TERRITOIRE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ backgroundColor: '#0a1c35', border: '1px solid rgba(0,200,255,0.08)', borderRadius: '8px', color: '#ddeeff', fontSize: '12px' }} />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '10px', color: 'rgba(150,200,240,0.4)' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Barres horizontales domaine */}
        <div className="bg-ocean-panel border border-ocean-border rounded-xl p-4">
          <p className="font-mono text-xs text-ocean-muted uppercase tracking-widest mb-3">Par domaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              layout="vertical"
              data={byDomaine}
              margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 10, fill: 'rgba(150,200,240,0.4)' }} axisLine={{ stroke: 'rgba(0,200,255,0.1)' }} tickLine={false} />
              <YAxis type="category" dataKey="domaine" tick={{ fontSize: 9, fill: 'rgba(150,200,240,0.4)' }} width={80} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#0a1c35', border: '1px solid rgba(0,200,255,0.08)', borderRadius: '8px', color: '#ddeeff', fontSize: '12px' }} />
              <Bar dataKey="count" fill="#00c8ff" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 5 sources */}
      <div className="bg-ocean-panel border border-ocean-border rounded-xl p-4 max-w-sm">
        <p className="font-mono text-xs text-ocean-muted uppercase tracking-widest mb-3">Top 5 sources</p>
        <table className="w-full text-sm">
          <thead>
            <tr className="font-mono text-xs text-ocean-muted border-b border-ocean-border">
              <th className="text-left py-1 font-medium">Source</th>
              <th className="text-right py-1 font-medium">Marchés</th>
            </tr>
          </thead>
          <tbody>
            {topSources.map(({ source, count }) => (
              <tr key={source} className="border-b border-ocean-cyan/4">
                <td className="py-1.5 font-sans text-sm text-ocean-text/80">{source}</td>
                <td className="py-1.5 text-right font-mono text-sm font-semibold text-ocean-text">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
