import axios from 'axios'
import type {
  AgentService,
  ServiceCreateRequest,
  ServiceResponse,
  ServiceListResponse,
  ConnectionListResponse,
  RoutingRuleListResponse,
  SystemStats,
  RoutingRule
} from '@/types/api'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

export const serviceApi = {
  // Service management
  async getServices(): Promise<AgentService[]> {
    const response = await api.get<ServiceListResponse>('/services')
    return response.data.items
  },

  async getService(serviceId: string): Promise<AgentService> {
    const response = await api.get<ServiceResponse>(`/services/${serviceId}`)
    return response.data.service
  },

  async createService(data: ServiceCreateRequest): Promise<AgentService> {
    const response = await api.post<ServiceResponse>('/services', data)
    return response.data.service
  },

  async deleteService(serviceId: string): Promise<void> {
    await api.delete(`/services/${serviceId}`)
  },

  async startService(serviceId: string): Promise<AgentService> {
    const response = await api.post<ServiceResponse>(`/services/${serviceId}/start`)
    return response.data.service
  },

  async stopService(serviceId: string): Promise<AgentService> {
    const response = await api.post<ServiceResponse>(`/services/${serviceId}/stop`)
    return response.data.service
  },

  async restartService(serviceId: string): Promise<AgentService> {
    const response = await api.post<ServiceResponse>(`/services/${serviceId}/restart`)
    return response.data.service
  },

  // Connections
  async getConnections() {
    const response = await api.get<ConnectionListResponse>('/connections')
    return response.data.items
  },

  async disconnectConnection(connectionId: string): Promise<void> {
    await api.delete(`/connections/${connectionId}`)
  },

  // Routing rules
  async getRoutingRules() {
    const response = await api.get<RoutingRuleListResponse>('/routing/rules')
    return response.data.items
  },

  async createRoutingRule(rule: Omit<RoutingRule, 'rule_id'>): Promise<RoutingRule> {
    const response = await api.post('/routing/rules', rule)
    return response.data.rule
  },

  async updateRoutingRule(ruleId: string, rule: Partial<RoutingRule>): Promise<RoutingRule> {
    const response = await api.put(`/routing/rules/${ruleId}`, rule)
    return response.data.rule
  },

  async deleteRoutingRule(ruleId: string): Promise<void> {
    await api.delete(`/routing/rules/${ruleId}`)
  },

  // Statistics
  async getStats() {
    const response = await api.get<SystemStats>('/stats')
    return response.data
  }
}

export default api