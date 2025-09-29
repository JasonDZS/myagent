import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AgentService, ServiceCreateRequest } from '@/types/api'
import { serviceApi } from '@/utils/api'

export const useServicesStore = defineStore('services', () => {
  const services = ref<AgentService[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const runningServices = computed(() => 
    services.value.filter(s => s.status === 'running')
  )

  const stoppedServices = computed(() => 
    services.value.filter(s => s.status === 'stopped')
  )

  const errorServices = computed(() => 
    services.value.filter(s => s.status === 'error')
  )

  async function fetchServices() {
    loading.value = true
    error.value = null
    try {
      services.value = await serviceApi.getServices()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch services'
    } finally {
      loading.value = false
    }
  }

  async function createService(data: ServiceCreateRequest) {
    try {
      const newService = await serviceApi.createService(data)
      services.value.push(newService)
      return newService
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create service'
      throw err
    }
  }

  async function startService(serviceId: string) {
    try {
      const updatedService = await serviceApi.startService(serviceId)
      const index = services.value.findIndex(s => s.service_id === serviceId)
      if (index !== -1) {
        services.value[index] = updatedService
      }
      return updatedService
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to start service'
      throw err
    }
  }

  async function stopService(serviceId: string) {
    try {
      const updatedService = await serviceApi.stopService(serviceId)
      const index = services.value.findIndex(s => s.service_id === serviceId)
      if (index !== -1) {
        services.value[index] = updatedService
      }
      return updatedService
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to stop service'
      throw err
    }
  }

  async function restartService(serviceId: string) {
    try {
      const updatedService = await serviceApi.restartService(serviceId)
      const index = services.value.findIndex(s => s.service_id === serviceId)
      if (index !== -1) {
        services.value[index] = updatedService
      }
      return updatedService
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to restart service'
      throw err
    }
  }

  async function deleteService(serviceId: string) {
    try {
      await serviceApi.deleteService(serviceId)
      services.value = services.value.filter(s => s.service_id !== serviceId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete service'
      throw err
    }
  }

  return {
    services,
    loading,
    error,
    runningServices,
    stoppedServices,
    errorServices,
    fetchServices,
    createService,
    startService,
    stopService,
    restartService,
    deleteService
  }
})