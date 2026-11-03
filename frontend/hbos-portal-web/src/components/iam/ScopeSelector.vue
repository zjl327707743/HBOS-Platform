<script setup lang="ts">
import { computed } from 'vue'

// The responsible scope is never inferred from the person's or department's own
// organisation: it must be chosen explicitly, and the exact wording differs per
// role so a clerk's departments cannot be mistaken for a company-wide grant.
const props = withDefaults(defineProps<{
  roleKey: string
  modelValue: string[]
  departments?: Array<{ value: string; label: string }>
  companies?: Array<{ value: string; label: string }>
  disabled?: boolean
  error?: string
  loading?: boolean
}>(), { departments: () => [], companies: () => [], disabled: false, error: '', loading: false })
const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const hint = computed(() => props.roleKey === 'clerk'
  ? '必须明确选择负责部门，不自动包含下级部门。'
  : props.roleKey === 'admin'
    ? '只能选择一个公司；不授予平台管理能力。'
    : props.roleKey === 'staff' ? '每位员工只查看自己的考勤，不需要另外选择。' : '')
const many = computed(() => props.roleKey === 'clerk')
const selectionText = computed(() => {
  if (props.roleKey === 'staff') return '仅本人'
  if (!props.modelValue.length) return props.roleKey === 'clerk' ? '尚未选择负责部门' : '尚未选择负责公司'
  return props.modelValue.length === 1 ? '已选择 1 个范围' : `已选择 ${props.modelValue.length} 个部门`
})
function update(value: unknown) {
  const rows = Array.isArray(value) ? value.map(String) : value ? [String(value)] : []
  emit('update:modelValue', props.roleKey === 'admin' ? rows.slice(0, 1) : rows)
}
</script>

<template>
  <div class="r6-scope-selector" :data-role="roleKey">
    <div v-if="roleKey === 'staff'" class="r6-scope-static">
      <strong>仅本人</strong>
      <span>每名员工只读取本人考勤与月度结果，不读取同部门其他人。</span>
    </div>
    <template v-else-if="roleKey === 'clerk'">
      <a-select :value="modelValue" mode="multiple" show-search option-filter-prop="label" :options="departments" placeholder="搜索并选择负责部门，可多选" aria-label="负责部门" :disabled="disabled || loading" class="r6-scope-control" :status="error ? 'error' : undefined" @update:value="update" />
      <p v-if="error" class="r6-field-error" role="alert">{{ error }}</p>
      <p v-else class="r6-field-hint">{{ hint }} {{ selectionText }}。</p>
    </template>
    <template v-else-if="roleKey === 'admin'">
      <a-select :value="modelValue[0]" show-search option-filter-prop="label" :options="companies" placeholder="选择一个负责公司" aria-label="负责公司" :disabled="disabled || loading" class="r6-scope-control" :status="error ? 'error' : undefined" @update:value="update" />
      <p v-if="error" class="r6-field-error" role="alert">{{ error }}</p>
      <p v-else class="r6-field-hint">{{ hint }}</p>
    </template>
    <div v-else class="r6-scope-static">
      <strong>不通过部门分配角色</strong>
      <span>不从此部门获得考勤角色；登录账号、个人安排与其他应用保持不变。</span>
    </div>
    <p v-if="many && !disabled" class="r6-scope-note">负责范围是业务对象，不等于员工所属部门；主部门变动不会自动扩大负责范围。</p>
  </div>
</template>
