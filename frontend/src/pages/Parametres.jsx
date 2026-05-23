import { useState } from 'react'
import DuplicatePair from '../components/DuplicatePair'
import { THEME_KEY, DEFAULTS, hexToRgbString, applyTheme } from '../utils/theme'
import {
  useAnalyzePending,
  useDuplicates,
  useDetectDuplicates,
  useResolveDuplicate,
  useArchiveOld,
  useResetDb,
  useCredentials,
  useSaveCredential,
  useDeleteCredential,
  useTestCredential,
} from '../hooks/useTenders'

const SITE_LOGOS = {
  nukema: '🏢',
  marcheonline: '🛒',
  instao: '🔑',
  marches_securises: '🔒',
  tendersgo: '🌍',
  vaao: '📋',
  dept974: '🏝️',
  marchespublicsinfo: '📢',
}

const SITE_URLS = {
  nukema: 'https://www.actu.nukema.com',
  marcheonline: 'https://www.marchesonline.com',
  instao: 'https://www.instao.fr',
  marches_securises: 'https://www.marches-securises.fr',
  tendersgo: 'https://app.tendersgo.com',
  vaao: 'https://www.vaao.re',
  dept974: 'https://marchespublics.la-reunion.fr',
  marchespublicsinfo: 'https://www.marches-publics.info',
}

function TabButton({ active, onClick, children, badge }) {
  return (
    <button
      onClick={onClick}
      className={`relative px-4 py-2 font-sans text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
        active
          ? 'border-ocean-cyan text-ocean-cyan'
          : 'border-transparent text-ocean-muted hover:text-ocean-text hover:border-ocean-border'
      }`}
    >
      {children}
      {badge > 0 && (
        <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 font-mono text-xs font-bold rounded-full bg-ocean-coral text-white">
          {badge}
        </span>
      )}
    </button>
  )
}

// ── Onglet Connexion ──────────────────────────────────────────────────────────

function ConnexionTab() {
  const { data: sites = [], refetch, isError } = useCredentials()
  const { mutate: save, isPending: saving } = useSaveCredential()
  const { mutate: remove, isPending: deleting } = useDeleteCredential()
  const { mutate: test, isPending: testing } = useTestCredential()

  const [open, setOpen] = useState(null)
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [canSave, setCanSave] = useState(false)

  const authenticated = sites.filter((s) => s.has_login_url)
  const publicSites = sites.filter((s) => !s.has_login_url)

  const openSite = (site) => {
    if (open === site) { closeSite(); return }
    setOpen(site)
    const entry = sites.find((s) => s.site === site)
    setForm({ email: entry?.email ?? '', password: '' })
    setShowPwd(false)
    setTestResult(null)
    setCanSave(false)
  }

  const closeSite = () => {
    setOpen(null)
    setTestResult(null)
    setCanSave(false)
  }

  const handleTest = () => {
    setTestResult(null)
    setCanSave(false)
    test(
      { site: open, email: form.email, password: form.password },
      {
        onSuccess: (data) => { setTestResult(data); setCanSave(data.ok) },
        onError: () => setTestResult({ ok: false, message: 'Erreur réseau' }),
      }
    )
  }

  const handleSave = () => {
    save(
      { site: open, email: form.email, password: form.password },
      { onSuccess: () => { refetch(); closeSite() } }
    )
  }

  const handleDelete = (site) => {
    remove({ site }, { onSuccess: () => refetch() })
  }

  const statusBadge = (status) => {
    if (status === 'configured')
      return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-teal/10 text-ocean-teal font-medium">● Configuré</span>
    if (status === 'env_override')
      return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-cyan/10 text-ocean-cyan font-medium">● Variable d'env</span>
    return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-coral/10 text-ocean-coral font-medium">● Non configuré</span>
  }

  const SiteRow = ({ entry }) => (
    <div className="border border-ocean-border rounded-lg overflow-hidden">
      <button
        onClick={() => openSite(entry.site)}
        className="w-full flex items-center justify-between px-4 py-3 font-sans text-sm hover:bg-ocean-cyan/4 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-lg flex-shrink-0">{SITE_LOGOS[entry.site] ?? '🌐'}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-ocean-text">{entry.label}</span>
              {statusBadge(entry.status)}
            </div>
            {entry.email && (
              <p className="font-mono text-xs text-ocean-muted mt-0.5 truncate">{entry.email}</p>
            )}
            {SITE_URLS[entry.site] && (
              <p className="font-mono text-xs text-ocean-muted truncate">{SITE_URLS[entry.site]}</p>
            )}
          </div>
        </div>
        <span className="text-ocean-muted text-xs flex-shrink-0 ml-2">{open === entry.site ? '▲' : '▼'}</span>
      </button>

      {open === entry.site && entry.status !== 'env_override' && (
        <div className="px-4 pb-4 pt-3 border-t border-ocean-border bg-ocean-navy">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">Adresse email / identifiant</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => { setForm((f) => ({ ...f, email: e.target.value })); setCanSave(false) }}
                className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
                placeholder="email@exemple.com"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">Mot de passe</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => { setForm((f) => ({ ...f, password: e.target.value })); setCanSave(false) }}
                  className="w-full px-3 py-2 pr-9 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ocean-muted hover:text-ocean-text"
                  title={showPwd ? 'Masquer' : 'Afficher'}
                >
                  {showPwd ? '🙈' : '👁️'}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {entry.has_login_url && (
              <button
                onClick={handleTest}
                disabled={testing || !form.email || !form.password}
                className="px-3 py-1.5 bg-ocean-cyan/12 text-ocean-cyan font-sans text-xs rounded-md border border-ocean-cyan/20 hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
              >
                {testing ? '⏳ Test…' : '🔌 Tester la connexion'}
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={saving || (entry.has_login_url && !canSave) || !form.email || !form.password}
              className="px-3 py-1.5 bg-ocean-cyan/12 text-ocean-cyan font-sans text-xs rounded-md border border-ocean-cyan/20 hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Sauvegarde…' : '💾 Sauvegarder'}
            </button>
            {entry.status === 'configured' && (
              <button
                onClick={() => handleDelete(entry.site)}
                disabled={deleting}
                className="px-3 py-1.5 bg-ocean-coral/10 text-ocean-coral font-sans text-xs rounded-md border border-ocean-coral/20 hover:bg-ocean-coral/18 disabled:opacity-50 transition-colors"
              >
                Supprimer
              </button>
            )}
          </div>

          {testResult && (
            <p className={`font-sans text-xs mt-2 font-medium ${testResult.ok ? 'text-ocean-teal' : 'text-ocean-coral'}`}>
              {testResult.ok ? '✓ Connexion réussie — vous pouvez sauvegarder' : `✗ ${testResult.message}`}
            </p>
          )}

          {entry.has_login_url && !testResult && form.email && form.password && (
            <p className="font-sans text-xs mt-2 text-ocean-muted">Testez la connexion avant de sauvegarder.</p>
          )}
          {!entry.has_login_url && (
            <p className="font-sans text-xs mt-2 text-ocean-muted">Ce site utilise les identifiants pour filtrer les résultats (pas de page de connexion à tester).</p>
          )}
        </div>
      )}

      {open === entry.site && entry.status === 'env_override' && (
        <div className="px-4 py-3 border-t border-ocean-border bg-ocean-cyan/4">
          <p className="font-sans text-xs text-ocean-cyan">
            ℹ️ Les identifiants sont définis via variable d'environnement et ne peuvent pas être modifiés ici.
          </p>
        </div>
      )}
    </div>
  )

  if (isError) {
    return (
      <div className="p-4 bg-ocean-coral/8 border border-ocean-coral/20 rounded-lg font-sans text-sm text-ocean-coral space-y-2">
        <p className="font-medium">⚠ Impossible de contacter le backend (<code>/api/credentials</code> — 404)</p>
        <p>Le serveur ne reconnaît pas encore cette route. Redémarrez le backend :</p>
        <ol className="list-decimal list-inside space-y-1 text-ocean-coral/80">
          <li>Fermez la fenêtre <strong>Backend FastAPI</strong></li>
          <li>Relancez via <code>start.bat</code> ou <code>.\start.ps1</code></li>
        </ol>
        <button
          onClick={() => refetch()}
          className="mt-2 px-3 py-1.5 bg-ocean-coral/10 text-ocean-coral font-sans text-xs rounded border border-ocean-coral/20 hover:bg-ocean-coral/18"
        >
          Réessayer
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <p className="font-sans text-sm text-ocean-muted">
        Configurez les identifiants pour les sites qui nécessitent une connexion. Ils sont chiffrés et stockés localement.
      </p>

      <div>
        <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest mb-3">
          🔐 Sites avec authentification
        </h3>
        <div className="space-y-2">
          {authenticated.map((entry) => (
            <SiteRow key={entry.site} entry={entry} />
          ))}
          {authenticated.length === 0 && (
            <p className="font-sans text-sm text-ocean-muted italic">Chargement…</p>
          )}
        </div>
      </div>

      {publicSites.length > 0 && (
        <div>
          <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest mb-3">
            📂 Sites avec identifiants optionnels
          </h3>
          <div className="space-y-2">
            {publicSites.map((entry) => (
              <SiteRow key={entry.site} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Onglet Analyse ────────────────────────────────────────────────────────────

function AnalyseTab() {
  const { mutate: analyze, isPending, data } = useAnalyzePending()
  return (
    <div className="space-y-4">
      <p className="font-sans text-sm text-ocean-muted">
        Lance l'analyse IA sur les marchés qui n'ont pas encore été analysés.
      </p>
      <button
        onClick={() => analyze()}
        disabled={isPending}
        className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
      >
        {isPending ? 'Analyse en cours…' : 'Analyser les marchés en attente'}
      </button>
      {data && (
        <p className="font-sans text-sm text-ocean-teal">✓ {data.message ?? 'Analyse lancée en arrière-plan.'}</p>
      )}
    </div>
  )
}

// ── Onglet Maintenance ────────────────────────────────────────────────────────

function MaintenanceTab() {
  const { data: duplicates = [], isLoading } = useDuplicates()
  const { mutate: detect, isPending: detecting, data: detectResult } = useDetectDuplicates()
  const { mutate: resolve } = useResolveDuplicate()
  const { mutate: archive, isPending: archiving, data: archiveResult } = useArchiveOld()
  const { mutate: reset, isPending: resetting } = useResetDb()
  const [showConfirm, setShowConfirm] = useState(false)

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">🔍 Doublons</h3>
        <div className="flex items-center gap-4">
          <button
            onClick={() => detect()}
            disabled={detecting}
            className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
          >
            {detecting ? 'Détection en cours…' : 'Détecter les doublons'}
          </button>
          {detectResult !== undefined && (
            <p className="font-sans text-sm text-ocean-text/80">{detectResult?.new_pairs ?? 0} nouvelle(s) paire(s) détectée(s).</p>
          )}
        </div>
        {isLoading && <p className="font-sans text-sm text-ocean-muted">Chargement…</p>}
        {!isLoading && duplicates.length === 0 && (
          <p className="font-sans text-sm text-ocean-muted">Aucun doublon non résolu.</p>
        )}
        <div className="space-y-3">
          {duplicates.map((pair) => (
            <DuplicatePair key={pair.id} pair={pair} onResolve={resolve} />
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">🛠️ Base de données</h3>
        <div className="flex flex-wrap gap-3 items-center">
          <button
            onClick={() => archive()}
            disabled={archiving}
            className="px-4 py-2 bg-ocean-panel border border-ocean-border text-ocean-text/80 font-sans text-sm rounded-lg hover:bg-ocean-cyan/4 disabled:opacity-50 transition-colors"
          >
            {archiving ? 'Archivage…' : 'Archiver les marchés > 30 jours'}
          </button>
          {archiveResult && (
            <span className="font-sans text-sm text-ocean-text/80">✓ {archiveResult.archived ?? 0} archivé(s)</span>
          )}
        </div>
        <div>
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="px-4 py-2 bg-ocean-coral/10 text-ocean-coral font-sans text-sm rounded-lg border border-ocean-coral/20 hover:bg-ocean-coral/18 transition-colors"
            >
              Réinitialiser la base de données
            </button>
          ) : (
            <div className="flex items-center gap-3 p-3 bg-ocean-coral/8 border border-ocean-coral/20 rounded-lg">
              <p className="font-sans text-sm text-ocean-coral font-medium">⚠️ Action irréversible. Confirmer ?</p>
              <button
                onClick={() => { reset(); setShowConfirm(false) }}
                disabled={resetting}
                className="px-3 py-1.5 bg-ocean-coral text-white font-sans text-xs rounded-lg hover:bg-ocean-coral/80 disabled:opacity-50"
              >
                Oui, réinitialiser
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 bg-ocean-panel text-ocean-text/80 font-sans text-xs rounded-lg border border-ocean-border hover:bg-ocean-cyan/4"
              >
                Annuler
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Onglet Apparence ──────────────────────────────────────────────────────────

const COLOR_FIELDS = [
  { key: 'deep',  label: 'Fond',              desc: 'Arrière-plan principal de l\'app', },
  { key: 'cyan',  label: 'Couleur principale', desc: 'Liens, boutons, éléments actifs',  },
  { key: 'coral', label: 'Alerte',             desc: 'Erreurs, dangers, badges urgents', },
  { key: 'text',  label: 'Texte',              desc: 'Couleur du texte principal',       },
]

function rgbStringToHex(rgb) {
  if (!rgb || typeof rgb !== 'string') return '#000000'
  return '#' + rgb.split(' ').map((n) => parseInt(n).toString(16).padStart(2, '0')).join('')
}

function ApparenceTab() {
  const [colors, setColors] = useState(() => {
    const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null') ?? DEFAULTS
    return {
      deep:  saved.deep  ?? DEFAULTS.deep,
      cyan:  saved.cyan  ?? DEFAULTS.cyan,
      coral: saved.coral ?? DEFAULTS.coral,
      text:  saved.text  ?? DEFAULTS.text,
    }
  })

  const handleChange = (key, hex) => {
    const rgb = hexToRgbString(hex)
    if (rgb === null) return
    setColors((prev) => ({ ...prev, [key]: rgb }))
    applyTheme({ [key]: rgb })
  }

  const handleApply = () => {
    localStorage.setItem(THEME_KEY, JSON.stringify(colors))
  }

  const handleReset = () => {
    setColors({ ...DEFAULTS })
    applyTheme(DEFAULTS)
    localStorage.removeItem(THEME_KEY)
  }

  return (
    <div className="space-y-6">
      <p className="font-sans text-sm text-ocean-muted">
        Personnalisez les couleurs de l'interface. Les changements sont appliqués immédiatement.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {COLOR_FIELDS.map(({ key, label, desc }) => (
          <div key={key} className="flex items-center gap-3 p-3 bg-ocean-panel border border-ocean-border rounded-lg">
            <label
              className="w-10 h-10 rounded-lg border-2 border-white/15 flex-shrink-0 cursor-pointer overflow-hidden relative"
              style={{ background: rgbStringToHex(colors[key]) }}
            >
              <input
                type="color"
                value={rgbStringToHex(colors[key])}
                onChange={(e) => handleChange(key, e.target.value)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </label>
            <div className="min-w-0">
              <div className="font-sans text-sm font-medium text-ocean-text">{label}</div>
              <div className="font-sans text-xs text-ocean-muted">{desc}</div>
              <div className="font-mono text-xs text-ocean-muted mt-0.5">{rgbStringToHex(colors[key])}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-4 border-t border-ocean-border">
        <button
          onClick={handleApply}
          className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 transition-colors"
        >
          💾 Appliquer
        </button>
        <button
          onClick={handleReset}
          className="px-4 py-2 bg-ocean-panel border border-ocean-border text-ocean-muted font-sans text-sm rounded-lg hover:bg-ocean-cyan/4 transition-colors"
        >
          Réinitialiser
        </button>
      </div>

      <p className="font-sans text-xs text-ocean-muted italic">
        Cliquez sur "Appliquer" pour sauvegarder vos choix entre les sessions.
      </p>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

const TABS = [
  { id: 'connexion',   label: '🔐 Connexion' },
  { id: 'analyse',     label: '🤖 Analyse' },
  { id: 'maintenance', label: '🛠️ Maintenance' },
  { id: 'apparence',   label: '🎨 Apparence' },
]

export default function Parametres() {
  const [activeTab, setActiveTab] = useState('connexion')
  const { data: creds = [] } = useCredentials()
  const missingCount = creds.filter((c) => c.status === 'missing').length

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="font-serif text-lg font-bold text-ocean-text mb-1">Paramètres</h1>
        <p className="font-sans text-sm text-ocean-muted">Gérez les connexions aux sites et la maintenance.</p>
      </div>

      <div className="border-b border-ocean-border mb-6 flex gap-0 -mx-1 overflow-x-auto">
        {TABS.map((tab) => (
          <TabButton
            key={tab.id}
            active={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            badge={tab.id === 'connexion' ? missingCount : 0}
          >
            {tab.label}
          </TabButton>
        ))}
      </div>

      <div>
        {activeTab === 'connexion' && <ConnexionTab />}
        {activeTab === 'analyse' && <AnalyseTab />}
        {activeTab === 'maintenance' && <MaintenanceTab />}
        {activeTab === 'apparence' && <ApparenceTab />}
      </div>
    </div>
  )
}
