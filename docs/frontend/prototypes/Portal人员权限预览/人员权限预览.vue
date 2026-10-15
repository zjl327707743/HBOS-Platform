<template>
  <section class="product-page iam-page">
    <div class="page-heading iam-page-heading">
      <div>
        <span class="page-kicker">平台管理 / 人员与权限</span>
        <h1>人员与权限</h1>
        <p>按组织岗位管理人员与角色，日常维护集中在这里。</p>
      </div>
      <span class="iam-preview-status"><i></i>Portal 组合稿 · 待确认</span>
    </div>
    <div ref="host" class="iam-preview-host"></div>
  </section>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import content from './内容容器.html?raw'
import styles from './原型样式.css?inline'
import { mountPermissionPrototype } from './岗位关联演示.js'
const host = ref<HTMLElement | null>(null)
const route = useRoute()
const router = useRouter()
let controller: { setPage: (page: 'people' | 'roles') => void; destroy: () => void } | undefined
onMounted(() => {
  const root = host.value!.attachShadow({ mode: 'open' })
  root.innerHTML = `<style>${styles}</style>${content}`
  controller = mountPermissionPrototype(root, route.path.endsWith('/roles') ? 'roles' : 'people', (page: string) => {
    void router.push(`/hbos/admin/${page === 'roles' ? 'roles' : 'people'}`)
  })
})
watch(() => route.path, path => controller?.setPage(path.endsWith('/roles') ? 'roles' : 'people'))
onBeforeUnmount(() => controller?.destroy())
</script>
<style>
.iam-page { gap:18px; }
.iam-page-heading { min-height:100px; align-items:center; padding:4px 5px 0; }
.iam-page .page-kicker { font-size:11px; font-weight:500; letter-spacing:0; }
.iam-page-heading h1 { margin:7px 0 8px; }
.iam-page-heading p { color:#7687a3; font-size:13px; }
.iam-preview-host { display:block; min-width:0; }
.iam-preview-status { display:inline-flex; gap:7px; align-items:center; color:#8796ad; border:1px solid rgba(114,130,157,.13); background:rgba(255,255,255,.5); border-radius:999px; padding:6px 11px; font-size:11px; white-space:nowrap; }
.iam-preview-status i { width:5px; height:5px; border-radius:50%; background:#8e94dc; }
@media(max-width:767px){.iam-page-heading{min-height:auto;padding:7px 3px;gap:10px}.iam-preview-status{align-self:flex-start}.iam-page{gap:13px;padding-bottom:70px}}
</style>
