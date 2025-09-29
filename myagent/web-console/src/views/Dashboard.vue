<template>
  <div class="dashboard">
    <!-- System Overview Cards -->
    <el-row :gutter="20" class="overview-cards">
      <el-col :span="6">
        <el-card class="overview-card services">
          <div class="card-content">
            <div class="card-info">
              <div class="card-value">{{ statsStore.stats.services.total }}</div>
              <div class="card-label">Total Services</div>
              <div class="card-sublabel">{{ statsStore.stats.services.running }} running</div>
            </div>
            <el-icon class="card-icon"><Setting /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card connections">
          <div class="card-content">
            <div class="card-info">
              <div class="card-value">{{ statsStore.stats.connections.total_connections }}</div>
              <div class="card-label">Total Connections</div>
              <div class="card-sublabel">{{ Object.values(statsStore.stats.connections.by_status).reduce((a, b) => a + b, 0) }} active</div>
            </div>
            <el-icon class="card-icon"><Connection /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card error-rate">
          <div class="card-content">
            <div class="card-info">
              <div class="card-value">{{ statsStore.stats.services.error }}</div>
              <div class="card-label">Error Services</div>
              <div class="card-sublabel">Services in error state</div>
            </div>
            <el-icon class="card-icon"><Warning /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="overview-card uptime">
          <div class="card-content">
            <div class="card-info">
              <div class="card-value">{{ statsStore.stats.health.healthy }}</div>
              <div class="card-label">Healthy Services</div>
              <div class="card-sublabel">{{ statsStore.stats.health.total }} total health checks</div>
            </div>
            <el-icon class="card-icon"><Timer /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card title="Service Status Distribution">
          <template #header>
            <div class="chart-header">
              <span>Service Status Distribution</span>
              <el-button @click="refreshCharts" size="small">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <v-chart :option="serviceStatusChart" style="height: 300px;" />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="chart-header">
              <span>Connection Trends</span>
              <el-button @click="toggleAutoRefresh" size="small" :type="autoRefresh ? 'primary' : 'default'">
                <el-icon><Timer /></el-icon>
                {{ autoRefresh ? 'Stop' : 'Start' }} Auto Refresh
              </el-button>
            </div>
          </template>
          <v-chart :option="connectionTrendChart" style="height: 300px;" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Service Health Status -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>Service Health Status</span>
          </template>
          <el-table :data="servicesStore.services" style="width: 100%">
            <el-table-column prop="name" label="Service Name" width="200" />
            <el-table-column label="Status" width="120">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small">
                  {{ scope.row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Type" width="120">
              <template #default="scope">
                <el-tag type="info" size="small">
                  {{ scope.row.agent_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="host" label="Host" width="120" />
            <el-table-column prop="port" label="Port" width="80" />
            <el-table-column label="Version" width="100">
              <template #default="scope">
                {{ scope.row.version }}
              </template>
            </el-table-column>
            <el-table-column label="Restart Count" width="120">
              <template #default="scope">
                {{ scope.row.restart_count }}
              </template>
            </el-table-column>
            <el-table-column label="Created At" min-width="180">
              <template #default="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useStatsStore } from '@/stores/stats'
import { useServicesStore } from '@/stores/services'
import { useConnectionsStore } from '@/stores/connections'

use([
  CanvasRenderer,
  PieChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const statsStore = useStatsStore()
const servicesStore = useServicesStore()
const connectionsStore = useConnectionsStore()

const autoRefresh = ref(true)
const connectionHistory = ref<Array<{ time: string, connections: number }>>([])
let refreshTimer: number | null = null

const serviceStatusChart = computed(() => {
  const running = servicesStore.runningServices.length
  const stopped = servicesStore.stoppedServices.length
  const error = servicesStore.errorServices.length
  
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      left: 'left',
    },
    series: [
      {
        name: 'Service Status',
        type: 'pie',
        radius: '50%',
        data: [
          { value: running, name: 'Running', itemStyle: { color: '#67c23a' } },
          { value: stopped, name: 'Stopped', itemStyle: { color: '#909399' } },
          { value: error, name: 'Error', itemStyle: { color: '#f56c6c' } }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
})

const connectionTrendChart = computed(() => {
  return {
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: connectionHistory.value.map(item => item.time)
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: 'Active Connections',
        type: 'line',
        data: connectionHistory.value.map(item => item.connections),
        itemStyle: { color: '#409eff' },
        areaStyle: { color: 'rgba(64, 158, 255, 0.2)' }
      }
    ]
  }
})

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    running: 'success',
    stopped: 'info',
    starting: 'warning',
    stopping: 'warning',
    error: 'danger'
  }
  return types[status] || 'info'
}

const getHealthType = (health: string) => {
  const types: Record<string, string> = {
    HEALTHY: 'success',
    UNHEALTHY: 'danger',
    UNKNOWN: 'warning'
  }
  return types[health] || 'warning'
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

const formatUptime = (seconds: number) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  
  if (days > 0) {
    return `${days}d ${hours}h`
  } else {
    return `${hours}h`
  }
}

const formatUptimeDetail = (seconds: number) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  return `${days}d ${hours}h ${minutes}m`
}

const refreshData = async () => {
  await Promise.all([
    statsStore.fetchStats(),
    servicesStore.fetchServices(),
    connectionsStore.fetchConnections()
  ])
  
  // Update connection history
  const now = new Date().toLocaleTimeString()
  connectionHistory.value.push({
    time: now,
    connections: statsStore.stats.connections.total_connections
  })
  
  // Keep only last 20 data points
  if (connectionHistory.value.length > 20) {
    connectionHistory.value.shift()
  }
}

const refreshCharts = async () => {
  await refreshData()
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    refreshTimer = setInterval(refreshData, 5000)
  } else {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }
}

onMounted(async () => {
  await refreshData()
  
  // Start auto refresh
  if (autoRefresh.value) {
    refreshTimer = setInterval(refreshData, 5000)
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview-cards {
  margin-bottom: 20px;
}

.overview-card {
  height: 120px;
}

.overview-card .el-card__body {
  padding: 20px;
  height: 100%;
}

.card-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.card-info {
  flex: 1;
}

.card-value {
  font-size: 32px;
  font-weight: bold;
  line-height: 1;
  margin-bottom: 5px;
}

.card-label {
  font-size: 16px;
  color: #303133;
  margin-bottom: 2px;
}

.card-sublabel {
  font-size: 12px;
  color: #909399;
}

.card-icon {
  font-size: 48px;
  opacity: 0.8;
}

.overview-card.services .card-value {
  color: #409eff;
}

.overview-card.services .card-icon {
  color: #409eff;
}

.overview-card.connections .card-value {
  color: #67c23a;
}

.overview-card.connections .card-icon {
  color: #67c23a;
}

.overview-card.error-rate .card-value {
  color: #f56c6c;
}

.overview-card.error-rate .card-icon {
  color: #f56c6c;
}

.overview-card.uptime .card-value {
  color: #e6a23c;
}

.overview-card.uptime .card-icon {
  color: #e6a23c;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>