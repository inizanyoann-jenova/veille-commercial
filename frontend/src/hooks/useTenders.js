import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTenders,
  getTender,
  getKpisPublic,
  getKpisCa,
  getKpisPriv,
  getPipeline,
  getUrgences,
  getScraperRuns,
  getSources,
  getChartData,
  collect,
  analyzePending,
  updateStatus,
  updateSaved,
  updateNotes,
  updateTags,
  updateAmount,
  deleteTender,
  analyzeTender,
} from '../services/api'

export const useTenders = (params) =>
  useQuery({
    queryKey: ['tenders', params],
    queryFn: () => getTenders(params),
    staleTime: 30_000,
  })

export const useTender = (id) =>
  useQuery({
    queryKey: ['tender', id],
    queryFn: () => getTender(id),
    enabled: Boolean(id),
  })

export const useKpisPublic = () =>
  useQuery({ queryKey: ['kpis', 'public'], queryFn: getKpisPublic, staleTime: 30_000 })

export const useKpisCa = () =>
  useQuery({ queryKey: ['kpis', 'ca'], queryFn: getKpisCa, staleTime: 30_000 })

export const useKpisPriv = () =>
  useQuery({ queryKey: ['kpis', 'priv'], queryFn: getKpisPriv, staleTime: 30_000 })

export const usePipeline = () =>
  useQuery({ queryKey: ['pipeline'], queryFn: getPipeline, staleTime: 30_000 })

export const useUrgences = () =>
  useQuery({
    queryKey: ['urgences'],
    queryFn: getUrgences,
    staleTime: 60_000,
    refetchInterval: 120_000,
  })

export const useScraperRuns = () =>
  useQuery({
    queryKey: ['scraper-runs'],
    queryFn: getScraperRuns,
    staleTime: 10_000,
    refetchInterval: 30_000,
  })

export const useSources = () =>
  useQuery({ queryKey: ['sources'], queryFn: getSources, staleTime: 60_000 })

export const useChartData = () =>
  useQuery({ queryKey: ['chart-data'], queryFn: getChartData, staleTime: 120_000 })

// ── Mutations ─────────────────────────────────────────────────────────────────

export const useCollectMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: collect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scraper-runs'] }),
  })
}

export const useUpdateStatus = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }) => updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })
}

export const useUpdateSaved = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_saved }) => updateSaved(id, is_saved),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}

export const useUpdateNotes = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }) => updateNotes(id, notes),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useUpdateTags = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, tags }) => updateTags(id, tags),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useUpdateAmount = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, amount }) => updateAmount(id, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
    },
  })
}

export const useDeleteTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteTender,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}

export const useAnalyzeTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }) => analyzeTender(id),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useAnalyzePending = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: analyzePending,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}
