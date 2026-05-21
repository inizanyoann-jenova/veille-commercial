import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Tenders ───────────────────────────────────────────────────────────────────

export const getTenders = (params) =>
  api.get('/tenders', { params }).then((r) => r.data)

export const getTender = (id) =>
  api.get(`/tenders/${id}`).then((r) => r.data)

export const updateStatus = (id, status) =>
  api.post(`/tenders/${id}/status`, { status }).then((r) => r.data)

export const updateNotes = (id, notes) =>
  api.post(`/tenders/${id}/notes`, { notes }).then((r) => r.data)

export const updateTags = (id, tags) =>
  api.post(`/tenders/${id}/tags`, { tags }).then((r) => r.data)

export const updateAmount = (id, amount) =>
  api.post(`/tenders/${id}/amount`, { amount }).then((r) => r.data)

export const updateSaved = (id, is_saved) =>
  api.post(`/tenders/${id}/saved`, { is_saved }).then((r) => r.data)

export const deleteTender = (id) =>
  api.delete(`/tenders/${id}`).then((r) => r.data)

export const analyzeTender = (id) =>
  api.post(`/tenders/${id}/analyze`).then((r) => r.data)

// ── KPIs ──────────────────────────────────────────────────────────────────────

export const getKpisPublic = () =>
  api.get('/kpis/public').then((r) => r.data)

export const getKpisCa = () =>
  api.get('/kpis/ca').then((r) => r.data)

export const getKpisPriv = () =>
  api.get('/kpis/priv').then((r) => r.data)

// ── Pipeline & Urgences ───────────────────────────────────────────────────────

export const getPipeline = () =>
  api.get('/pipeline').then((r) => r.data)

export const getUrgences = (params) =>
  api.get('/urgences', { params }).then((r) => r.data)

// ── Collecte & analyse ────────────────────────────────────────────────────────

export const collect = (source_names = null) =>
  api.post('/collect', { source_names }).then((r) => r.data)

export const analyzePending = () =>
  api.post('/analyze-pending').then((r) => r.data)

export const detectDuplicates = () =>
  api.post('/detect-duplicates').then((r) => r.data)

// ── Scraper runs ──────────────────────────────────────────────────────────────

export const getScraperRuns = (limit = 50) =>
  api.get('/scraper-runs', { params: { limit } }).then((r) => r.data)

// ── Sources ───────────────────────────────────────────────────────────────────

export const getSources = () =>
  api.get('/sources').then((r) => r.data)

// ── Charts ────────────────────────────────────────────────────────────────────

export const getChartData = (max_rows = 5000) =>
  api.get('/chart-data', { params: { max_rows } }).then((r) => r.data)

// ── Admin ─────────────────────────────────────────────────────────────────────

export const resetDb = () =>
  api.post('/admin/reset-db').then((r) => r.data)

export const archiveOld = (days = 30) =>
  api.post('/admin/archive-old', null, { params: { days } }).then((r) => r.data)

export default api
