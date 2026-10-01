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
      @click="openResult(result)"
    >
      <div class="command-result-icon" :class="result.appId"><component :is="appIcon(result.appId)" /></div>
      <div>
        <strong>{{ result.title }}</strong>
        <span>{{ result.appTitle }} · {{ result.typeLabel }} · {{ result.subtitle }}</span>
      </div>
      <ArrowRightOutlined class="result-arrow" />
    </button>

    <a-alert v-if="errorMessage" type="error" show-icon :message="errorMessage" />
    <a-empty v-else-if="!loading && !results.length" :description="query ? '未找到匹配结果' : '输入关键词开始搜索'" />
  </a-modal>
</template>

<script setup lang="ts">
import { nextTick, ref, toRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRightOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import { searchPortal } from '@/services/portalProvider'
import { openBusinessRoute } from '@/services/businessNavigation'
import { appIcon } from '@/components/appIcons'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import type { SearchResultDTO } from '@/contracts/portal'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()
const router = useRouter()
const query = ref('')
const { results, errorMessage, loading } = useDebouncedSearch(query, toRef(props, 'open'), searchPortal)
const selectedIndex = ref(0)
const inputRef = ref()

function move(delta: number) {
  const total = results.value.length
  if (!total) return
  selectedIndex.value = (selectedIndex.value + delta + total) % total
}

function activateSelected() {
  if (selectedIndex.value < results.value.length) {
    const result = results.value[selectedIndex.value]
    if (result) openResult(result)
    return
  }
}

function openResult(result: SearchResultDTO) {
  emit('close')
  void openBusinessRoute(router, result.appId, result.deepLink)
}

watch(() => props.open, async (value) => {
  if (value) {
    await nextTick()
    inputRef.value?.focus?.()
  }
})
watch(results, () => { selectedIndex.value = 0 })
</script>
