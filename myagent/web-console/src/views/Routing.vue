<template>
  <div class="routing-view">
    <div class="actions-bar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        Create Rule
      </el-button>
      <el-button @click="refreshRules" :loading="routingStore.loading">
        <el-icon><Refresh /></el-icon>
        Refresh
      </el-button>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>Routing Rules ({{ routingStore.rules.length }})</span>
          <div class="rule-stats">
            <el-tag type="success">
              Enabled: {{ enabledRules.length }}
            </el-tag>
            <el-tag type="info">
              Disabled: {{ disabledRules.length }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-table
        :data="routingStore.rules"
        v-loading="routingStore.loading"
        style="width: 100%"
        :default-sort="{ prop: 'priority', order: 'ascending' }"
      >
        <el-table-column prop="priority" label="Priority" width="80" sortable />
        <el-table-column prop="name" label="Rule Name" width="200" />
        <el-table-column label="Conditions" min-width="200">
          <template #default="scope">
            <div class="conditions">
              <el-tag
                v-for="(value, key) in scope.row.conditions"
                :key="key"
                size="small"
                class="condition-tag"
              >
                {{ key }}: {{ value }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Target Tags" width="150">
          <template #default="scope">
            <div class="tags">
              <el-tag
                v-for="tag in scope.row.target_tags"
                :key="tag"
                size="small"
                type="info"
              >
                {{ tag }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="strategy" label="Strategy" width="150">
          <template #default="scope">
            <el-tag :type="getStrategyType(scope.row.strategy)" size="small">
              {{ formatStrategy(scope.row.strategy) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Status" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.enabled"
              @change="updateRuleStatus(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="150" fixed="right">
          <template #default="scope">
            <el-button-group>
              <el-button
                size="small"
                @click="editRule(scope.row)"
              >
                Edit
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

    <!-- Create/Edit Rule Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingRule ? 'Edit Routing Rule' : 'Create Routing Rule'"
      width="700px"
    >
      <el-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="ruleRules"
        label-width="120px"
      >
        <el-form-item label="Rule Name" prop="name">
          <el-input v-model="ruleForm.name" placeholder="Enter rule name" />
        </el-form-item>
        
        <el-form-item label="Priority" prop="priority">
          <el-input-number
            v-model="ruleForm.priority"
            :min="0"
            :max="100"
            placeholder="Rule priority (0-100)"
          />
          <div class="form-help">Lower numbers have higher priority</div>
        </el-form-item>
        
        <el-form-item label="Strategy" prop="strategy">
          <el-select v-model="ruleForm.strategy" placeholder="Select routing strategy">
            <el-option label="Round Robin" value="round_robin" />
            <el-option label="Least Connections" value="least_connections" />
            <el-option label="Hash Based" value="hash_based" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="Target Tags" prop="target_tags">
          <el-select
            v-model="ruleForm.target_tags"
            multiple
            filterable
            allow-create
            placeholder="Select or create tags"
            style="width: 100%"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
          <div class="form-help">Services with these tags will be considered for routing</div>
        </el-form-item>
        
        <el-form-item label="Conditions">
          <div class="conditions-editor">
            <div
              v-for="(condition, index) in ruleForm.conditions"
              :key="index"
              class="condition-row"
            >
              <el-input
                v-model="condition.key"
                placeholder="Condition key"
                style="width: 200px"
              />
              <el-input
                v-model="condition.value"
                placeholder="Condition value"
                style="width: 200px"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeCondition(index)"
              >
                Remove
              </el-button>
            </div>
            <el-button @click="addCondition" size="small">
              <el-icon><Plus /></el-icon>
              Add Condition
            </el-button>
          </div>
          <div class="form-help">
            Conditions for when this rule should be applied (e.g., client_ip: 192.168.1.*)
          </div>
        </el-form-item>
        
        <el-form-item label="Enabled">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="cancelEdit">Cancel</el-button>
        <el-button type="primary" @click="saveRule" :loading="saving">
          {{ editingRule ? 'Update' : 'Create' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useRoutingStore } from '@/stores/routing'
import { useServicesStore } from '@/stores/services'
import type { RoutingRule } from '@/types/api'

const routingStore = useRoutingStore()
const servicesStore = useServicesStore()

const showCreateDialog = ref(false)
const editingRule = ref<RoutingRule | null>(null)
const saving = ref(false)
const ruleFormRef = ref<FormInstance>()

const ruleForm = ref({
  name: '',
  priority: 50,
  strategy: 'round_robin' as 'round_robin' | 'least_connections' | 'hash_based',
  target_tags: [] as string[],
  conditions: [] as Array<{ key: string, value: string }>,
  enabled: true
})

const ruleRules: FormRules = {
  name: [
    { required: true, message: 'Please input rule name', trigger: 'blur' }
  ],
  priority: [
    { required: true, message: 'Please input priority', trigger: 'blur' }
  ],
  strategy: [
    { required: true, message: 'Please select strategy', trigger: 'change' }
  ]
}

const enabledRules = computed(() => 
  routingStore.rules.filter(r => r.enabled)
)

const disabledRules = computed(() => 
  routingStore.rules.filter(r => !r.enabled)
)

const availableTags = computed(() => {
  const tags = new Set<string>()
  servicesStore.services.forEach(service => {
    service.tags.forEach(tag => tags.add(tag))
  })
  return Array.from(tags)
})

const getStrategyType = (strategy: string) => {
  const types: Record<string, string> = {
    round_robin: 'primary',
    least_connections: 'success',
    hash_based: 'warning'
  }
  return types[strategy] || 'primary'
}

const formatStrategy = (strategy: string) => {
  const formats: Record<string, string> = {
    round_robin: 'Round Robin',
    least_connections: 'Least Connections',
    hash_based: 'Hash Based'
  }
  return formats[strategy] || strategy
}

const refreshRules = async () => {
  await routingStore.fetchRules()
}

const updateRuleStatus = async (rule: RoutingRule) => {
  try {
    await routingStore.updateRule(rule.rule_id, { enabled: rule.enabled })
    ElMessage.success(`Rule ${rule.enabled ? 'enabled' : 'disabled'} successfully`)
  } catch (error) {
    ElMessage.error('Failed to update rule status')
    // Revert the change
    rule.enabled = !rule.enabled
  }
}

const editRule = (rule: RoutingRule) => {
  editingRule.value = rule
  ruleForm.value = {
    name: rule.name,
    priority: rule.priority,
    strategy: rule.strategy,
    target_tags: [...rule.target_tags],
    conditions: Object.entries(rule.conditions).map(([key, value]) => ({ key, value: String(value) })),
    enabled: rule.enabled
  }
  showCreateDialog.value = true
}

const addCondition = () => {
  ruleForm.value.conditions.push({ key: '', value: '' })
}

const removeCondition = (index: number) => {
  ruleForm.value.conditions.splice(index, 1)
}

const saveRule = async () => {
  if (!ruleFormRef.value) return
  
  const valid = await ruleFormRef.value.validate()
  if (!valid) return
  
  saving.value = true
  try {
    // Convert conditions array back to object
    const conditions: Record<string, any> = {}
    ruleForm.value.conditions.forEach(condition => {
      if (condition.key && condition.value) {
        conditions[condition.key] = condition.value
      }
    })
    
    const ruleData = {
      name: ruleForm.value.name,
      priority: ruleForm.value.priority,
      strategy: ruleForm.value.strategy,
      target_tags: ruleForm.value.target_tags,
      conditions,
      enabled: ruleForm.value.enabled
    }
    
    if (editingRule.value) {
      await routingStore.updateRule(editingRule.value.rule_id, ruleData)
      ElMessage.success('Rule updated successfully')
    } else {
      await routingStore.createRule(ruleData)
      ElMessage.success('Rule created successfully')
    }
    
    showCreateDialog.value = false
    cancelEdit()
  } catch (error) {
    ElMessage.error(editingRule.value ? 'Failed to update rule' : 'Failed to create rule')
  } finally {
    saving.value = false
  }
}

const cancelEdit = () => {
  editingRule.value = null
  ruleForm.value = {
    name: '',
    priority: 50,
    strategy: 'round_robin',
    target_tags: [],
    conditions: [],
    enabled: true
  }
  ruleFormRef.value?.resetFields()
}

const confirmDelete = async (rule: RoutingRule) => {
  try {
    await ElMessageBox.confirm(
      `This will permanently delete routing rule "${rule.name}". Continue?`,
      'Warning',
      {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    await routingStore.deleteRule(rule.rule_id)
    ElMessage.success('Rule deleted successfully')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete rule')
    }
  }
}

onMounted(async () => {
  await Promise.all([
    routingStore.fetchRules(),
    servicesStore.fetchServices()
  ])
})
</script>

<style scoped>
.routing-view {
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

.rule-stats {
  display: flex;
  gap: 10px;
}

.conditions, .tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.condition-tag {
  margin: 2px;
}

.conditions-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.condition-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>