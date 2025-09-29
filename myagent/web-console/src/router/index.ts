import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Services from '@/views/Services.vue'
import Connections from '@/views/Connections.vue'
import Routing from '@/views/Routing.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/services',
      name: 'services',
      component: Services
    },
    {
      path: '/connections',
      name: 'connections',
      component: Connections
    },
    {
      path: '/routing',
      name: 'routing',
      component: Routing
    }
  ]
})

export default router