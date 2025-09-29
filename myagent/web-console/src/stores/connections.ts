import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionInfo } from '@/types/api'
import { serviceApi } from '@/utils/api'

export const useConnectionsStore = defineStore('connections', () => {
  const connections = ref<ConnectionInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeConnections = computed(() => 
    connections.value.filter(c => c.status === 'ACTIVE')
  )

  const idleConnections = computed(() => 
    connections.value.filter(c => c.status === 'IDLE')
  )

  const totalConnections = computed(() => connections.value.length)

  async function fetchConnections() {
    loading.value = true
    error.value = null
    try {
      connections.value = await serviceApi.getConnections()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch connections'
    } finally {
      loading.value = false
    }
  }

  async function disconnectConnection(connectionId: string) {
    try {
      await serviceApi.disconnectConnection(connectionId)
      connections.value = connections.value.filter(c => c.connection_id !== connectionId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to disconnect connection'
      throw err
    }
  }

  return {
    connections,
    loading,
    error,
    activeConnections,
    idleConnections,
    totalConnections,
    fetchConnections,
    disconnectConnection
  }
})