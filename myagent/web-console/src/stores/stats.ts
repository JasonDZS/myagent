import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SystemStats } from '@/types/api'
import { serviceApi } from '@/utils/api'

export const useStatsStore = defineStore('stats', () => {
  const stats = ref<SystemStats>({
    services: {
      total: 0,
      running: 0,
      stopped: 0,
      error: 0,
      unhealthy: 0
    },
    connections: {
      total_connections: 0,
      by_status: {},
      by_service: {}
    },
    health: {
      total: 0,
      healthy: 0,
      unhealthy: 0,
      degraded: 0,
      unknown: 0
    }
  })
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      stats.value = await serviceApi.getStats()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch stats'
    } finally {
      loading.value = false
    }
  }

  function startAutoRefresh(interval = 5000) {
    const timer = setInterval(fetchStats, interval)
    return () => clearInterval(timer)
  }

  return {
    stats,
    loading,
    error,
    fetchStats,
    startAutoRefresh
  }
})