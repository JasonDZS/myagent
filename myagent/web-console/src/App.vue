<template>
  <el-container class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>MyAgent</h2>
        <p>WebSocket Manager</p>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
        text-color="#fff"
        active-text-color="#409eff"
        background-color="#2c3e50"
      >
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>Dashboard</span>
        </el-menu-item>
        <el-menu-item index="/services">
          <el-icon><Setting /></el-icon>
          <span>Services</span>
        </el-menu-item>
        <el-menu-item index="/connections">
          <el-icon><Connection /></el-icon>
          <span>Connections</span>
        </el-menu-item>
        <el-menu-item index="/routing">
          <el-icon><Share /></el-icon>
          <span>Routing</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-title">
          <h3>{{ getPageTitle() }}</h3>
        </div>
        <div class="header-actions">
          <el-button @click="refreshData" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
            Refresh
          </el-button>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useServicesStore } from '@/stores/services'
import { useConnectionsStore } from '@/stores/connections'
import { useStatsStore } from '@/stores/stats'

const route = useRoute()
const servicesStore = useServicesStore()
const connectionsStore = useConnectionsStore()
const statsStore = useStatsStore()

const refreshing = ref(false)

const getPageTitle = () => {
  const titles: Record<string, string> = {
    '/': 'Dashboard',
    '/services': 'Services Management',
    '/connections': 'Connections Monitor',
    '/routing': 'Routing Rules'
  }
  return titles[route.path] || 'MyAgent Manager'
}

const refreshData = async () => {
  refreshing.value = true
  try {
    await Promise.all([
      servicesStore.fetchServices(),
      connectionsStore.fetchConnections(),
      statsStore.fetchStats()
    ])
  } finally {
    refreshing.value = false
  }
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #2c3e50;
  color: white;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #34495e;
}

.logo h2 {
  margin: 0;
  color: #409eff;
}

.logo p {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #bdc3c7;
}

.sidebar-menu {
  border: none;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-title h3 {
  margin: 0;
  color: #303133;
}

.main-content {
  background-color: #f5f5f5;
  padding: 20px;
}
</style>