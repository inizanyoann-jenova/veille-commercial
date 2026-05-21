import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
      defaults: {},
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    })),
  },
}))

describe('api service', () => {
  it('exports getTenders as a function', async () => {
    const { getTenders } = await import('./api.js')
    expect(typeof getTenders).toBe('function')
  })

  it('exports getKpisPublic as a function', async () => {
    const { getKpisPublic } = await import('./api.js')
    expect(typeof getKpisPublic).toBe('function')
  })

  it('exports collect as a function', async () => {
    const { collect } = await import('./api.js')
    expect(typeof collect).toBe('function')
  })

  it('exports updateStatus as a function', async () => {
    const { updateStatus } = await import('./api.js')
    expect(typeof updateStatus).toBe('function')
  })
})
