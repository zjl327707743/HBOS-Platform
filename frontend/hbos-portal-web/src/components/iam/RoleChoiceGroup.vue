<script setup lang="ts">
import { computed } from 'vue'
import { InfoCircleOutlined, SafetyCertificateOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons-vue'
import { boundaryText, rolePurpose, roleTitle, ROLE_KEYS } from '@/services/assignmentPresentation'

// Department and employee surfaces share this one published-catalogue picker.
// A catalogue entry that is missing or not grantable is never rendered as an
// offer: the card stays visible with the server's reason and is not selectable.
const props = withDefaults(defineProps<{
  modelValue: string
  catalog?: Array<{ role_key: string; title?: string; boundary_kind?: string; grantable?: boolean; reason?: string; published_revision?: number }> | null
  disabled?: boolean
  name: string
  label?: string
}>(), { catalog: null, disabled: false, label: '默认角色' })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const icons: Record<string, unknown> = { staff: UserOutlined, clerk: TeamOutlined, admin: SafetyCertificateOutlined }
const cards = computed(() => ROLE_KEYS.map(key => {
  const entry = (props.catalog || []).find(row => row.role_key === key)
  const published = Boolean(entry && (entry.published_revision ?? 0) > 0)
  // No catalogue row means "not confirmed as grantable", never "grantable".
  const grantable = Boolean(entry && entry.grantable === true && published)
  const reason = entry?.reason || (entry ? '当前不能授予这个角色。' : '角色目录暂无法读取，不能授予。')
  return {
    key,
    title: roleTitle(key, entry?.title),
    purpose: rolePurpose[key] || '用途待核对',
    boundary: boundaryText(entry?.boundary_kind),
    icon: icons[key] || UserOutlined,
    grantable,
    reason: grantable ? '' : reason,
    revision: entry?.published_revision,
  }
}))
function choose(key: string, grantable: boolean) {
  if (props.disabled || !grantable) return
  emit('update:modelValue', key)
}
</script>

<template>
  <div class="r6-role-picker">
    <div class="r6-role-grid" role="radiogroup" :aria-label="label">
      <label v-for="card in cards" :key="card.key" class="r6-choice-card" :class="{ selected: modelValue === card.key, blocked: !card.grantable }" :data-selected="modelValue === card.key" :data-role="card.key">
        <span class="r6-choice-card__icon" aria-hidden="true"><component :is="card.icon" /></span>
        <input type="radio" :name="name" :value="card.key" :checked="modelValue === card.key" :disabled="disabled || !card.grantable" @change="choose(card.key, card.grantable)" />
        <strong class="r6-choice-card__title">{{ card.title }}</strong>
        <span class="r6-choice-card__purpose">{{ card.purpose }}</span>
        <small class="r6-choice-card__scope">{{ card.boundary }}</small>
        <p v-if="!card.grantable" class="r6-choice-card__blocked"><InfoCircleOutlined /> {{ card.reason }}</p>
        <small v-else-if="card.revision" class="r6-choice-card__meta">已发布 v{{ card.revision }}</small>
      </label>
    </div>
  </div>
</template>
