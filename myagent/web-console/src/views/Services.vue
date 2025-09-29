<template>
  <div class="services-view">
    <div class="actions-bar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        Create Service
      </el-button>
      <el-button @click="refreshServices" :loading="servicesStore.loading">
        <el-icon><Refresh /></el-icon>
        Refresh
      </el-button>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>Services ({{ servicesStore.services.length }})</span>
          <div class="service-stats">
            <el-tag type="success">Running: {{ servicesStore.runningServices.length }}</el-tag>
            <el-tag type="info">Stopped: {{ servicesStore.stoppedServices.length }}</el-tag>
            <el-tag type="danger">Error: {{ servicesStore.errorServices.length }}</el-tag>
          </div>
        </div>
      </template>

      <el-table
        :data="servicesStore.services"
        v-loading="servicesStore.loading"
        style="width: 100%"
      >
        <el-table-column prop="name" label="Name" width="150" />
        <el-table-column prop="description" label="Description" />
        <el-table-column prop="host" label="Host" width="120" />
        <el-table-column prop="port" label="Port" width="80" />
        <el-table-column label="Status" width="100">
          <template #default="scope">
            <el-tag 
              :type="getStatusType(scope.row.status)"
              size="small"
            >
              {{ scope.row.status.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Type" width="100">
          <template #default="scope">
            {{ scope.row.agent_type }}
          </template>
        </el-table-column>
        <el-table-column label="Restart Count" width="120">
          <template #default="scope">
            {{ scope.row.restart_count }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="scope">
            <el-button-group>
              <el-button
                v-if="scope.row.status === 'stopped'"
                size="small"
                type="success"
                @click="startService(scope.row.service_id)"
              >
                Start
              </el-button>
              <el-button
                v-if="scope.row.status === 'running'"
                size="small"
                type="warning"
                @click="stopService(scope.row.service_id)"
              >
                Stop
              </el-button>
              <el-button
                v-if="scope.row.status === 'running'"
                size="small"
                @click="restartService(scope.row.service_id)"
              >
                Restart
              </el-button>
              <el-button
                size="small"
                type="danger"
                @click="confirmDelete(scope.row)"
              >
                Delete
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create Service Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      title="Create New Service"
      width="600px"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="140px"
      >
        <el-form-item label="Name" prop="name">
          <el-input v-model="createForm.name" placeholder="Service name" />
        </el-form-item>
        
        <el-form-item label="Description" prop="description">
          <el-input v-model="createForm.description" placeholder="Service description" />
        </el-form-item>
        
        <el-form-item label="Agent File" prop="agent_factory_path">
          <el-input v-model="createForm.agent_factory_path" placeholder="Path to agent factory file" />
        </el-form-item>
        
        <el-form-item label="Host" prop="host">
          <el-input v-model="createForm.host" placeholder="localhost" />
        </el-form-item>
        
        <el-form-item label="Port" prop="port">
          <el-input-number v-model="createForm.port" :min="1024" :max="65535" />
        </el-form-item>
        
        <el-form-item label="Tags" prop="tags">
          <el-select
            v-model="createForm.tags"
            multiple
            filterable
            allow-create
            placeholder="Add tags"
            style="width: 100%"
          >
          </el-select>
        </el-form-item>
        
        <el-form-item label="Auto Start">
          <el-switch v-model="createForm.auto_start" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createService" :loading="creating">
          Create
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useServicesStore } from '@/stores/services'
import type { ServiceCreateRequest, AgentService } from '@/types/api'

const servicesStore = useServicesStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()

const createForm = ref<ServiceCreateRequest>({
  name: '',
  description: '',
  agent_factory_path: '',
  host: 'localhost',
  port: undefined,
  tags: [],
  auto_start: false
})

const createRules: FormRules = {
  name: [
    { required: true, message: 'Please input service name', trigger: 'blur' }
  ],
  agent_factory_path: [
    { required: true, message: 'Please input agent factory path', trigger: 'blur' }
  ]
}

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

const refreshServices = async () => {
  await servicesStore.fetchServices()
}

const startService = async (serviceId: string) => {
  try {
    await servicesStore.startService(serviceId)
    ElMessage.success('Service started successfully')
  } catch (error) {
    ElMessage.error('Failed to start service')
  }
}

const stopService = async (serviceId: string) => {
  try {
    await servicesStore.stopService(serviceId)
    ElMessage.success('Service stopped successfully')
  } catch (error) {
    ElMessage.error('Failed to stop service')
  }
}

const restartService = async (serviceId: string) => {
  try {
    await servicesStore.restartService(serviceId)
    ElMessage.success('Service restarted successfully')
  } catch (error) {
    ElMessage.error('Failed to restart service')
  }
}

const confirmDelete = async (service: AgentService) => {
  try {
    await ElMessageBox.confirm(
      `This will permanently delete service "${service.name}". Continue?`,
      'Warning',
      {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    await servicesStore.deleteService(service.service_id)
    ElMessage.success('Service deleted successfully')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete service')
    }
  }
}

const createService = async () => {
  if (!createFormRef.value) return
  
  const valid = await createFormRef.value.validate()
  if (!valid) return
  
  creating.value = true
  try {
    await servicesStore.createService(createForm.value)
    ElMessage.success('Service created successfully')
    showCreateDialog.value = false
    resetCreateForm()
  } catch (error) {
    ElMessage.error('Failed to create service')
  } finally {
    creating.value = false
  }
}

const resetCreateForm = () => {
  createForm.value = {
    name: '',
    description: '',
    agent_factory_path: '',
    host: 'localhost',
    port: undefined,
    tags: [],
    auto_start: false
  }
  createFormRef.value?.resetFields()
}

onMounted(() => {
  servicesStore.fetchServices()
})
</script>

<style scoped>
.services-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.actions-bar {
  display: flex;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.service-stats {
  display: flex;
  gap: 10px;
}
</style>