<template>
  <section class="inventory-page">
    <div class="inventory-page-head">
      <div>
        <h1>{{ item?.label || '该功能' }}</h1>
        <p>{{ item?.hint || '出现在导航里的入口，前端页尚未实现。' }}</p>
      </div>
    </div>

    <section class="inventory-dest glass-surface">
      <div class="inventory-dest-group">
        <div class="inventory-state">
          <ToolOutlined class="inventory-state-icon" />
          <h3>这个功能的前端页还没有做出来</h3>
          <p>
            入口已经在导航里占位，点进来看到的是这一页。它不会跳去别的系统，
            也不会假装能用——等前端页做出来后，同一个入口就直接打开了。
          </p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="$router.push('/hbos/inventory')">
              返回库存概览
            </a-button>
            <a-button @click="$router.push('/hbos/apps')">查看可用应用</a-button>
          </div>
        </div>
      </div>

      <div v-if="fallback" class="inventory-dest-group">
        <h3>现在可以做什么</h3>
        <p style="margin: 0 0 12px; color: var(--hbos-text-secondary)">
          {{ fallback }}
        </p>
        <button type="button" class="inventory-dest-item" @click="goFallback">
          <CameraOutlined />
          <span class="inventory-dest-text">
            <b>入库拍照识别</b>
            <small>拍标签 → 识别 → 人工校对 → 生成草稿</small>
          </span>
          <RightOutlined />
        </button>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CameraOutlined,
  RightOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { findInventoryNavItem } from '@/data/inventoryNav'
import { openBusinessRoute } from '@/services/businessNavigation'

const route = useRoute()
const router = useRouter()

const item = computed(() => {
  const itemId = route.params.itemId
  return typeof itemId === 'string' ? findInventoryNavItem(itemId) : undefined
})

/** 入库作业类入口未实现时，指向已经可用的拍照识别页，给一条真实的下一步 */
const INTAKE_RELATED = new Set(['photo-intake', 'stock-entry', 'qa-release'])

const fallback = computed(() =>
  item.value && INTAKE_RELATED.has(item.value.id)
    ? '到货入库可以先走「入库拍照识别」——它会拍照识别标签、校对后生成草稿入库单。'
    : '',
)

function goFallback() {
  void openBusinessRoute(router, 'inventory', '/hbos/inventory/intake')
}
</script>
