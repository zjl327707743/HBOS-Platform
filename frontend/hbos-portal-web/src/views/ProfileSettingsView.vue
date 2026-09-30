<template>
  <section class="product-page">
    <div class="page-heading">
      <div>
        <span class="page-kicker">PROFILE & SETTINGS</span>
        <h1>我的与设置</h1>
        <p>管理账号安全与个人工作台体验。</p>
      </div>
    </div>

    <div class="profile-grid">
      <section class="profile-card glass-surface">
        <div class="profile-hero">
          <a-avatar :size="72" class="profile-avatar">{{ portal.user?.avatarText }}</a-avatar>
          <div>
            <h2>{{ portal.user?.displayName }}</h2>
            <p>{{ portal.user?.id }}</p>
            <a-tag color="blue">{{ portal.user?.roleLabel }}</a-tag>
            <a-tag>{{ portal.user?.department }}</a-tag>
          </div>
        </div>
        <a-divider />
        <a-descriptions :column="1" size="small">
          <a-descriptions-item label="默认入口">HBOS Workspace</a-descriptions-item>
          <a-descriptions-item label="登录方式">密码 / 本人飞书 · 统一账号</a-descriptions-item>
          <a-descriptions-item label="可用应用">{{ portal.apps.length }}</a-descriptions-item>
        </a-descriptions>
        <a-button v-if="deskAccess" block @click="openProfile">管理个人资料</a-button>
      </section>

      <section class="settings-stack">
        <AccountSecurity />
        <AppDiagnostics v-if="canDiagnose" />
        <div class="setting-card glass-surface">
          <div class="setting-head"><div><h3>外观体验</h3><p>跨应用偏好同步尚未实现，当前沿用已批准的默认体验。</p></div><BgColorsOutlined /></div>
          <div class="setting-row"><span>主题</span><a-segmented disabled v-model:value="theme" :options="['明亮', '跟随系统']" /></div>
          <div class="setting-row"><span>视觉动效</span><a-switch disabled v-model:checked="motion" checked-children="开启" un-checked-children="关闭" /></div>
          <div class="setting-row"><span>表格密度</span><a-segmented disabled v-model:value="density" :options="['舒适', '紧凑']" /></div>
        </div>

        <div class="setting-card glass-surface">
          <div class="setting-head"><div><h3>工作偏好</h3><p>个人偏好持久化尚未接入。</p></div><SlidersOutlined /></div>
          <div class="setting-row"><span>优先显示超期事项</span><a-switch disabled checked /></div>
          <div class="setting-row"><span>显示业务脉搏</span><a-switch disabled checked /></div>
          <div class="setting-row"><span>显示数字孪生入口</span><a-switch disabled checked /></div>
        </div>

        <div v-if="deskAccess" class="setting-card glass-surface management-entry">
          <div class="setting-head"><div><h3>Management Console</h3><p>仅管理员 / 实施人员 / 高级业务管理员可进入</p></div><SafetyCertificateOutlined /></div>
          <a-alert message="进入后将切换到 Frappe Desk 管理后台界面。" type="info" show-icon />
          <a-button style="margin-top: 14px" @click="openDesk">进入管理后台 <ArrowRightOutlined /></a-button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import AppDiagnostics from '@/components/account/AppDiagnostics.vue'
import { getSecurity } from '@/services/accountApi'
import {
  ArrowRightOutlined,
  BgColorsOutlined,
  SafetyCertificateOutlined,
  SlidersOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
const theme = ref('明亮')
const density = ref('舒适')
const motion = ref(true)
const deskAccess = ref(false)
const canDiagnose = ref(false)
function openDesk() { window.location.assign('/app') }
function openProfile() { if (portal.user) window.location.assign(`/app/user/${encodeURIComponent(portal.user.id)}`) }
onMounted(async () => { try { const security = await getSecurity(); deskAccess.value = security.desk_access; canDiagnose.value = security.can_admin_recover } catch { deskAccess.value = false } })
</script>
