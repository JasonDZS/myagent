export interface AgentService {
  service_id: string
  name: string
  description: string
  host: string
  port: number
  endpoint: string
  tags: string[]
  agent_type: string
  version: string
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error'
  created_at: string
  started_at?: string
  last_health_check?: string
  error_message?: string
  restart_count: number
}

export interface ServiceConfig {
  max_connections: number
  timeout: number
  restart_policy: 'never' | 'on_failure' | 'always'
  env_vars: Record<string, string>
  args: string[]
}

export interface ServiceStats {
  start_time?: string
  active_connections: number
  total_requests: number
  error_count: number
  last_health_check?: string
  health_status: 'HEALTHY' | 'UNHEALTHY' | 'UNKNOWN'
}

export interface ConnectionInfo {
  connection_id: string
  client_ip: string
  client_port: number
  service_id: string
  connected_at: string
  last_activity: string
  status: 'ACTIVE' | 'IDLE' | 'DISCONNECTED'
}

export interface RoutingRule {
  rule_id: string
  name: string
  priority: number
  conditions: Record<string, any>
  target_tags: string[]
  strategy: 'round_robin' | 'least_connections' | 'hash_based'
  enabled: boolean
}

export interface SystemStats {
  services: {
    total: number
    running: number
    stopped: number
    error: number
    unhealthy: number
  }
  connections: {
    total_connections: number
    by_status: Record<string, number>
    by_service: Record<string, number>
  }
  health: {
    total: number
    healthy: number
    unhealthy: number
    degraded: number
    unknown: number
  }
}

export interface ServiceCreateRequest {
  name: string
  description?: string
  agent_factory_path: string
  host?: string
  port?: number
  endpoint?: string
  tags?: string[]
  config?: Partial<ServiceConfig>
  auto_start?: boolean
}

export interface ServiceResponse {
  success: boolean
  service: AgentService
  message: string
}

export interface ServiceListResponse {
  items: AgentService[]
  total: number
  limit?: number
  offset: number
  has_more: boolean
}

export interface ConnectionListResponse {
  items: ConnectionInfo[]
  total: number
  limit?: number
  offset: number
  has_more: boolean
}

export interface RoutingRuleListResponse {
  items: RoutingRule[]
  total: number
  limit?: number
  offset: number
  has_more: boolean
}

