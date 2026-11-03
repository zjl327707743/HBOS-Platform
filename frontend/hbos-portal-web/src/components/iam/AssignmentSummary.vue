<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from './StatusTag.vue'
import { boundaryText, managementRole, roleTitle, scopeRefsOf } from '@/services/assignmentPresentation'

// One reading surface for "what is arranged now". It deliberately keeps four
// separate facts apart: source, role, responsible scope and what is actually
// usable — a saved or confirmed arrangement never implies effective access.
const props = withDefaults(defineProps<{
  source: 'FOLLOW_DEPARTMENT' | 'DIRECT' | 'NONE' | 'LEGACY' | 'UNKNOWN'
  roleKey?: string | null
  roleName?: string | null
  boundaryKind?: string | null
  scopes?: Array<{ scope_type?: string; scope_ref?: string; label?: string }> | null
  scopeLabels?: string[] | null
  effective?: boolean | null
  /** A department default is judged per follower, so a single boolean is wrong there. */
  statusLabel?: string
  statusTone?: 'neutral' | 'brand' | 'success' | 'warning' | 'error'
  statusDetail?: string
  reasons?: string[]
  sourceDetail?: string
  emptyText?: string
  compact?: boolean
}>(), { roleKey: '', roleName: '', boundaryKind: null, scopes: null, scopeLabels: null, effective: null, statusLabel: '', statusTone: undefined, statusDetail: '', reasons: () => [], sourceDetail: '', emptyText: '', compact: false })
const emit = defineEmits<{ 'view-detail': [] }>()

const sourceText = computed(() => ({
  FOLLOW_DEPARTMENT: '跟随部门默认',
  DIRECT: '单独设置',
  NONE: '不通过部门分配',
  LEGACY: '沿用原有安排',
  UNKNOWN: '来源待核对',
} as Record<string, string>)[props.source])
const roleText = computed(() => props.source === 'NONE' ? '不分配角色' : props.source === 'LEGACY' ? '以原有安排为准' : roleTitle(props.roleKey, props.roleName || undefined))
const scopeText = computed(() => {
  if (props.source === 'NONE') return '不提供角色功能'
  if (props.source === 'LEGACY') return '未覆盖现有安排'
  const labels = props.scopeLabels?.length ? props.scopeLabels : (props.scopes || []).map(row => row.label || row.scope_ref || '待核对范围')
  if (props.roleKey === 'staff') return '仅本人'
  if (!labels.length) return props.roleKey ? '负责范围待核对' : '仅本人'
  return labels.join('、')
})
const boundary = computed(() => boundaryText(props.boundaryKind || (props.roleKey === 'staff' ? 'SELF' : props.roleKey === 'clerk' ? 'DEPARTMENT' : props.roleKey === 'admin' ? 'COMPANY' : '')))
const pendingConfirmation = computed(() => managementRole(props.roleKey) && props.source === 'FOLLOW_DEPARTMENT')
const derivedTone = computed(() => props.effective === true ? 'success' as const : props.effective === false ? 'warning' as const : 'neutral' as const)
const derivedLabel = computed(() => props.effective === true ? '当前可用' : props.effective === false ? '当前暂不可用' : '实际状态待核对')
const tone = computed(() => props.statusTone || derivedTone.value)
const label = computed(() => props.statusLabel || derivedLabel.value)
const limitation = computed(() => props.reasons.filter(Boolean).join('；'))
const scopeCount = computed(() => props.scopeLabels?.length || scopeRefsOf(props.scopes).length)
</script>

<template>
  <section class="r6-assignment-summary" :class="{ 'is-compact': compact }" aria-label="当前安排">
    <div class="r6-assignment-summary__grid">
      <div class="r6-assignment-summary__item" data-fact="source">
        <span>来源</span>
        <strong>{{ sourceText }}</strong>
        <small v-if="sourceDetail">{{ sourceDetail }}</small>
      </div>
      <div class="r6-assignment-summary__item" data-fact="role">
        <span>角色</span>
        <strong>{{ roleText }}</strong>
        <small v-if="source !== 'NONE' && source !== 'LEGACY'">{{ boundary }}</small>
      </div>
      <div class="r6-assignment-summary__item" data-fact="scope">
        <span>负责范围</span>
        <strong class="r6-assignment-summary__scopes">{{ scopeText }}</strong>
        <small v-if="scopeCount > 1">共 {{ scopeCount }} 个明确范围，不含下级</small>
      </div>
      <div class="r6-assignment-summary__item" data-fact="status">
        <span>实际状态</span>
        <StatusTag :tone="tone">{{ label }}</StatusTag>
        <small v-if="statusDetail">{{ statusDetail }}</small>
        <small v-else-if="pendingConfirmation">管理型角色需逐人确认后才可使用</small>
      </div>
    </div>
    <p v-if="limitation" class="r6-assignment-summary__reason"><strong>限制仍保留：</strong>{{ limitation }}</p>
    <p v-else-if="emptyText" class="r6-assignment-summary__reason">{{ emptyText }}</p>
    <slot />
    <button v-if="$slots.detail" type="button" class="r6-assignment-summary__more" @click="emit('view-detail')">
      <slot name="detail" />
    </button>
  </section>
</template>
