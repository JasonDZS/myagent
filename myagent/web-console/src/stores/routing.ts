import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RoutingRule } from '@/types/api'
import { serviceApi } from '@/utils/api'

export const useRoutingStore = defineStore('routing', () => {
  const rules = ref<RoutingRule[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchRules() {
    loading.value = true
    error.value = null
    try {
      rules.value = await serviceApi.getRoutingRules()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch routing rules'
    } finally {
      loading.value = false
    }
  }

  async function createRule(rule: Omit<RoutingRule, 'rule_id'>) {
    try {
      const newRule = await serviceApi.createRoutingRule(rule)
      rules.value.push(newRule)
      return newRule
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create routing rule'
      throw err
    }
  }

  async function updateRule(ruleId: string, updates: Partial<RoutingRule>) {
    try {
      const updatedRule = await serviceApi.updateRoutingRule(ruleId, updates)
      const index = rules.value.findIndex(r => r.rule_id === ruleId)
      if (index !== -1) {
        rules.value[index] = updatedRule
      }
      return updatedRule
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update routing rule'
      throw err
    }
  }

  async function deleteRule(ruleId: string) {
    try {
      await serviceApi.deleteRoutingRule(ruleId)
      rules.value = rules.value.filter(r => r.rule_id !== ruleId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete routing rule'
      throw err
    }
  }

  return {
    rules,
    loading,
    error,
    fetchRules,
    createRule,
    updateRule,
    deleteRule
  }
})