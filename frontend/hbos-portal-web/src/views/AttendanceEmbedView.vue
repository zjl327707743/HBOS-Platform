<template>
  <section class="att-embed">
    <header class="att-embed-head">
      <div>
        <span class="page-kicker">ATTENDANCE · {{ item?.label || '业务页面' }}</span>
        <h1>{{ item?.label || '业务页面' }}</h1>
      </div>
      <a-tag v-if="stripped" color="green">已融入门户</a-tag>
    </header>

    <a-alert
      v-if="error"
      type="error"
      show-icon
      :message="error"
      description="该入口由后台页面承载。可重试一次；若仍失败，请改用侧栏底部的「管理后台」直接打开。"
      class="att-embed-alert"
    >
      <template #action>
        <a-button size="small" @click="load(slug)">重试</a-button>
      </template>
    </a-alert>

    <div v-else class="att-embed-frame-wrap glass-surface">
      <div v-if="loading" class="att-embed-loading">
        <a-spin />
        <p>正在载入 {{ item?.label }}…</p>
      </div>
      <iframe
        v-show="src && !loading"
        ref="frameRef"
        :src="src || 'about:blank'"
        :title="item?.label || '考勤业务页面'"
        class="att-embed-frame"
        @load="onFrameLoad"
      ></iframe>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { findNavBySlug } from '@/services/attendanceNav'
import { resolveBusinessRoute } from '@/services/portalProvider'
import { useDeskEmbed } from '@/composables/useDeskEmbed'

const route = useRoute()

const frameRef = ref<HTMLIFrameElement | null>(null)
const src = ref('')
const error = ref('')
const loading = ref(false)

const slug = computed(() => String(route.params.slug ?? ''))
const item = computed(() => findNavBySlug(slug.value))

const { stripped } = useDeskEmbed(frameRef)

async function load(targetSlug: string) {
  const target = findNavBySlug(targetSlug)
  src.value = ''
  error.value = ''
  loading.value = true

  if (!target) {
    error.value = '未知的考勤入口'
    loading.value = false
    return
  }
  if (target.kind !== 'embed') {
    // 原生入口不该走到这里；与其白屏，不如给一句能行动的话
    error.value = '该入口不走内嵌'
    loading.value = false
    return
  }

  try {
    // 后端是映射的权威：稳定路径 → Desk 实现路径，并在此过程中被
    // hbos_portal 的 validate_resolved_path 校验一次（拒 scheme / netloc /
    // fragment / `//` / 反斜杠 / 穿越段）。
    const resolved = await resolveBusinessRoute('attendance', target.stablePath)
    if (
      typeof resolved !== 'string'
      || !resolved.startsWith('/')
      || resolved.startsWith('//')
      || resolved.includes('\\')
    ) {
      error.value = '后台返回的页面地址无效'
      loading.value = false
      return
    }
    src.value = resolved
    // 真正的 loading 结束时机在 iframe 的 load 事件里——不在这里。
    // 若 URL 有缓存命中、load 已错过，onFrameLoad 也会兜底关掉。
  } catch (cause) {
    error.value = (cause instanceof Error && cause.message) || '业务页面加载失败'
    loading.value = false
  }
}

/**
 * iframe 加载完成才收起 loading。
 *
 * 之前直接写 `@load="loading = false"` 有两个问题：① `src=''` 时浏览器把空串
 * 解析成**当前文档 URL**，iframe 会先把门户自己加载一遍并触发 load，遮罩
 * 提前消失；② 请求还没发出就关掉了 loading。现在 src 用 `about:blank` 兜底，
 * 且只在真有 src 时才认定加载完成。
 */
function onFrameLoad() {
  if (src.value) loading.value = false
}

watch(slug, (value) => { if (value) load(value) }, { immediate: true })
</script>

<style scoped>
.att-embed { display: grid; gap: 16px; }

.att-embed-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.att-embed-head h1 { margin: 6px 0 0; font-size: 30px; line-height: 38px; }
.att-embed-alert { margin: 0; }

.att-embed-frame-wrap {
  position: relative;
  padding: 8px;
  border-radius: var(--hbos-radius-card);
  min-height: 70vh;
}
.att-embed-frame {
  display: block;
  width: 100%;
  height: 78vh;
  border: 0;
  border-radius: var(--hbos-radius-sm);
  background: #fff;
}

.att-embed-loading {
  position: absolute;
  inset: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--hbos-bg-elevated);
  border-radius: var(--hbos-radius-sm);
  color: var(--hbos-text-secondary);
  font-size: 14px;
}
.att-embed-loading p { margin: 0; }

@media (max-width: 720px) {
  .att-embed-head h1 { font-size: 20px; line-height: 28px; }
  .att-embed-frame { height: 70vh; }
}
</style>
