import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'
import { useTodoStore } from '@/stores/todo'

export interface FrappeUser {
  name: string
  full_name: string
  email?: string
  roles: string[]
  user_type?: string
}

export const useAuthStore = defineStore('auth', () => {
  const todoStore = useTodoStore()
  const user = ref<FrappeUser | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  function clearSessionState() {
    user.value = null
    initialized.value = false
    todoStore.clearForLogout()
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('hbos:auth-expired', clearSessionState)
  }

  const isLoggedIn = computed(() => !!user.value)

  /**
   * 探测当前 Frappe session。
   * 用 POST 调用 frappe.auth.get_logged_user（whitelist），
   * 返回 Guest 则未登录。
   */
  async function checkSession() {
    if (initialized.value) return isLoggedIn.value
    loading.value = true
    try {
      const res = await api.post('frappe.auth.get_logged_user', {})
      const loggedUser = res.data?.message
      if (loggedUser && loggedUser !== 'Guest') {
        user.value = {
          name: loggedUser,
          full_name: loggedUser,
          roles: [],
        }
        await fetchUserInfo(loggedUser)
      } else {
        user.value = null
      }
    } catch {
      user.value = null
    } finally {
      loading.value = false
      initialized.value = true
    }
    return isLoggedIn.value
  }

  async function fetchUserInfo(username: string) {
    try {
      const res = await api.post('frappe.client.get_list', {
        doctype: 'User',
        filters: { name: username },
        fields: ['name', 'full_name', 'email', 'user_type'],
        limit_page_length: 1,
      })
      const rows = res.data?.message
      if (Array.isArray(rows) && rows.length > 0) {
        const row = rows[0]
        user.value = {
          name: row.name,
          full_name: row.full_name || row.name,
          email: row.email,
          user_type: row.user_type,
          roles: user.value?.roles || [],
        }
      }
      await fetchUserRoles(username)
    } catch {
      // 忽略
    }
  }

  async function fetchUserRoles(username: string) {
    // 用 hb_lims_app 提供的 get_user_roles（基于 frappe.get_roles），
    // 避免直接读 Has Role（普通用户无权限，会触发 PermissionError）
    try {
      const res = await api.post('hb_lims_app.hbos_lims.lims_service.get_user_roles', { username })
      const roles = res.data?.message
      if (Array.isArray(roles)) {
        user.value = { ...user.value!, roles }
      }
    } catch {
      // 忽略角色获取失败
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const res = await api.post('login', { usr: username, pwd: password })
      const data = res.data
      if (data.message === 'Logged In') {
        user.value = {
          name: username,
          full_name: data.full_name || username,
          roles: [],
        }
        await fetchUserRoles(username)
        return true
      }
      return false
    } catch {
      return false
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  async function logout() {
    try {
      await api.post('logout')
    } finally {
      clearSessionState()
    }
  }

  return { user, loading, initialized, isLoggedIn, checkSession, login, logout }
})
