<template>
  <a-modal
    :open="open"
    :footer="null"
    :closable="false"
    width="700px"
    wrap-class-name="command-modal"
    @cancel="$emit('close')"
  >
    <div class="command-search">
      <SearchOutlined />
      <a-input
        ref="inputRef"
        v-model:value="query"
        bordered="false"
        placeholder="搜索应用、批次、样品、员工或输入命令…"
        aria-label="全局搜索"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="activateSelected"
        @keydown.esc.prevent="$emit('close')"
      />
      <kbd>ESC</kbd>
    </div>

    <div class="command-section-title">{{ query ? '搜索结果' : '建议' }}</div>
    <button
      v-for="(result, index) in results"
      :key="result.id"
      class="command-result"
      :class="{ selected: selectedIndex === index }"
      type="button"
      @mouseenter="selectedIndex = index"
      @click="go(result.deepLink)"
    >
      <div class="command-result-icon" :class="result.appId"><component :is="appIcon(result.appId)" /></div>
      <div>
        <strong>{{ result.title }}</strong>
        <span>{{ result.appTitle }} · {{ result.typeLabel }} · {{ result.subtitle }}</span>
      </div>
      <ArrowRightOutlined class="result-arrow" />
    </button>

    <div class="command-section-title">快速操作</div>
    <button
      class="command-result"
      :class="{ selected: selectedIndex === results.length }"
      type="button"
      @mouseenter="selectedIndex = results.length"
      @click="go('/hbos/work')"
    >
      <div class="command-result-icon inventory"><ScanOutlined /></div>
      <div><strong>扫码入库</strong><span>仓储 · 快捷操作</span></div>
      <ArrowRightOutlined class="result-arrow" />
    </button>
  </a-modal>
</template>

<script setup lang="ts">
import { nextTick, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ScanOutlined,
  SearchOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { searchPortal } from '@/services/portalProvider'
import type { SearchResultDTO } from '@/contracts/portal'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()
const router = useRouter()
const query = ref('')
const results = ref<SearchResultDTO[]>([])
const selectedIndex = ref(0)
const inputRef = ref()

const iconMap: Record<string, Component> = {
  lims: ExperimentOutlined,
  inventory: InboxOutlined,
  attendance: ClockCircleOutlined,
  equipment: ToolOutlined,
}

function appIcon(appId: string) {
  return iconMap[appId] || InboxOutlined
}

async function refresh() {
  results.value = await searchPortal(query.value)
  selectedIndex.value = 0
}

function move(delta: number) {
  const total = results.value.length + 1
  selectedIndex.value = (selectedIndex.value + delta + total) % total
}

function activateSelected() {
  if (selectedIndex.value < results.value.length) {
    const result = results.value[selectedIndex.value]
    if (result) go(result.deepLink)
    return
  }
  go('/hbos/work')
}

function go(path: string) {
  emit('close')
  void router.push(path)
}

watch(() => props.open, async (value) => {
  if (value) {
    await refresh()
    await nextTick()
    inputRef.value?.focus?.()
  }
})
watch(query, refresh)
</script>
