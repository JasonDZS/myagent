<template>
  <div class="connections-view">
    <div class="actions-bar">
      <el-button @click="refreshConnections" :loading="connectionsStore.loading">
        <el-icon><Refresh /></el-icon>
        Refresh
      </el-button>
      <el-switch
        v-model="autoRefresh"
        active-text="Auto Refresh"
        @change="toggleAutoRefresh"
      />
    </div>

    <div class="stats-cards">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ connectionsStore.totalConnections }}</div>
              <div class="stat-label">Total Connections</div>
            </div>
            <el-icon class="stat-icon" color="#409eff"><Connection /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value active">{{ connectionsStore.activeConnections.length }}</div>
              <div class="stat-label">Active</div>
            </div>
            <el-icon class="stat-icon" color="#67c23a"><CircleCheckFilled /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value idle">{{ connectionsStore.idleConnections.length }}</div>
              <div class="stat-label">Idle</div>
            </div>
            <el-icon class="stat-icon" color="#e6a23c"><Clock /></el-icon>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ servicesStore.runningServices.length }}</div>
              <div class="stat-label">Running Services</div>
            </div>
            <el-icon class="stat-icon" color="#67c23a"><Setting /></el-icon>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>Active Connections ({{ connectionsStore.connections.length }})</span>
          <div class="filter-controls">
            <el-select
              v-model="statusFilter"
              placeholder="Filter by status"
              clearable
              style="width: 150px"
              @change="filterConnections"
            >
              <el-option label="All" value="" />
              <el-option label="Active" value="ACTIVE" />
              <el-option label="Idle" value="IDLE" />
              <el-option label="Disconnected" value="DISCONNECTED" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredConnections"
        v-loading="connectionsStore.loading"
        style="width: 100%"
      >
        <el-table-column prop="connection_id" label="Connection ID" width="200">
          <template #default="scope">
            <code>{{ scope.row.connection_id.substring(0, 8) }}...</code>
          </template>
        </el-table-column>
        <el-table-column prop="client_ip" label="Client IP" width="120" />
        <el-table-column prop="client_port" label="Client Port" width="100" />
        <el-table-column label="Service" width="150">
          <template #default="scope">
            <span>{{ getServiceName(scope.row.service_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="100">
          <template #default="scope">
            <el-tag 
              :type="getStatusType(scope.row.status)"
              size="small"
            >
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Connected At" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.connected_at) }}
          </template>
        </el-table-column>
        <el-table-column label="Last Activity" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.last_activity) }}
          </template>
        </el-table-column>
        <el-table-column label="Duration" width="120">
          <template #default="scope">
            {{ getDuration(scope.row.connected_at) }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="120" fixed="right">
          <template #default="scope">
            <el-button
              size="small"
              type="danger"
              @click="confirmDisconnect(scope.row)"
              :disabled="scope.row.status === 'DISCONNECTED'"
            >
              Disconnect
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConnectionsStore } from '@/stores/connections'
import { useServicesStore } from '@/stores/services'
import type { ConnectionInfo } from '@/types/api'

const connectionsStore = useConnectionsStore()
const servicesStore = useServicesStore()

const autoRefresh = ref(false)
const statusFilter = ref('')
let refreshTimer: number | null = null

const filteredConnections = computed(() => {
  if (!statusFilter.value) {
    return connectionsStore.connections
  }
  return connectionsStore.connections.filter(conn => 
    conn.status === statusFilter.value
  )
})

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    ACTIVE: 'success',
    IDLE: 'warning',
    DISCONNECTED: 'info'
  }
  return types[status] || 'info'
}

const getServiceName = (serviceId: string) => {
  const service = servicesStore.services.find(s => s.service_id === serviceId)
  return service?.name || serviceId.substring(0, 8) + '...'
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

const getDuration = (connectedAt: string) => {
  const start = new Date(connectedAt)
  const now = new Date()
  const diffMs = now.getTime() - start.getTime()
  
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  const seconds = Math.floor((diffMs % (1000 * 60)) / 1000)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  } else {
    return `${seconds}s`
  }
}

const refreshConnections = async () => {
  await connectionsStore.fetchConnections()
}

const filterConnections = () => {
  // Trigger reactivity
}

const toggleAutoRefresh = (enabled: boolean) => {
  if (enabled) {
    refreshTimer = setInterval(refreshConnections, 5000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

const confirmDisconnect = async (connection: ConnectionInfo) => {
  try {
    await ElMessageBox.confirm(
      `This will disconnect client ${connection.client_ip}:${connection.client_port}. Continue?`,
      'Warning',
      {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    await connectionsStore.disconnectConnection(connection.connection_id)
    ElMessage.success('Connection disconnected successfully')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to disconnect connection')
    }
  }
}

onMounted(async () => {
  await Promise.all([
    connectionsStore.fetchConnections(),
    servicesStore.fetchServices()
  ])
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.connections-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  position: relative;
  overflow: hidden;
}

.stat-card .el-card__body {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-content {
  text-align: left;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.stat-value.active {
  color: #67c23a;
}

.stat-value.idle {
  color: #e6a23c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.stat-icon {
  font-size: 40px;
  opacity: 0.8;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>