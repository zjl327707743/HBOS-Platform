<script setup lang="ts" generic="T extends string | number">
import { CheckOutlined, CloseOutlined } from '@ant-design/icons-vue'
import { computed, nextTick, onBeforeUnmount, onDeactivated, ref, useId, watch, type CSSProperties } from 'vue'

type Option = { value: T; label: string; disabled?: boolean }
const props = defineProps<{
  value?: T; options: readonly Option[]; id?: string; placeholder?: string
  disabled?: boolean; searchable?: boolean; allowClear?: boolean
  ariaLabel?: string; ariaDescribedby?: string; ariaRequired?: boolean; ariaInvalid?: boolean
}>()
const emit = defineEmits<{ 'update:value': [value: T | undefined]; change: [value: T] }>()
const uid = useId()
const controlId = computed(() => props.id || uid)
const listId = uid + '-choices'
const anchor = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | HTMLInputElement | null>(null)
const popup = ref<HTMLElement | null>(null)
const opened = ref(false), active = ref(-1), query = ref(''), composing = ref(false)
const position = ref<CSSProperties>({})
const label = computed(() => props.options.find(option => option.value === props.value)?.label)
const matches = computed(() => {
  const term = props.searchable ? query.value.trim().toLocaleLowerCase() : ''
  return term ? props.options.filter(option => option.label.toLocaleLowerCase().includes(term)) : props.options
})
const available = computed(() => matches.value.flatMap((option, i) => option.disabled ? [] : [i]))
const optionId = (i: number) => listId + '-' + i
const description = computed(() => ({
  id: controlId.value,
  role: 'combobox',
  'aria-label': props.ariaLabel,
  'aria-describedby': props.ariaDescribedby,
  'aria-required': props.ariaRequired || undefined,
  'aria-invalid': props.ariaInvalid || undefined,
  'aria-expanded': opened.value,
  'aria-controls': opened.value ? listId : undefined,
  'aria-activedescendant': opened.value && active.value >= 0 ? optionId(active.value) : undefined,
  'aria-haspopup': 'listbox' as const,
  disabled: props.disabled,
}))

let prefix = '', prefixAt = 0

function place() {
  const rect = anchor.value?.getBoundingClientRect()
  if (!rect) return
  const margin = 12, gap = 6
  const width = Math.min(Math.max(rect.width, 220), window.innerWidth - margin * 2)
  const left = Math.min(Math.max(margin, rect.left), window.innerWidth - width - margin)
  const below = window.innerHeight - rect.bottom - margin - gap, above = rect.top - margin - gap
  const needed = Math.min(300, Math.max(1, matches.value.length) * 44 + 14)
  const up = below < needed && above > below
  position.value = {
    left: left + 'px', width: width + 'px',
    top: up ? undefined : (rect.bottom + gap) + 'px',
    bottom: up ? (window.innerHeight - rect.top + gap) + 'px' : undefined,
    maxHeight: Math.min(300, Math.max(0, up ? above : below)) + 'px',
  }
}
function setActive(index: number) {
  active.value = index
  void nextTick(() => {
    const list = popup.value, option = document.getElementById(optionId(active.value))
    if (!list || !option) return
    const viewport = list.getBoundingClientRect(), item = option.getBoundingClientRect()
    if (item.top < viewport.top + 5) list.scrollTop += item.top - viewport.top - 5
    else if (item.bottom > viewport.bottom - 5) list.scrollTop += item.bottom - viewport.bottom + 5
  })
}
function open(last = false) {
  if (opened.value || props.disabled) return
  place()
  opened.value = true
  const current = matches.value.findIndex(option => option.value === props.value && !option.disabled)
  setActive(current >= 0 ? current : (last ? available.value[available.value.length - 1] : available.value[0]) ?? -1)
  attach()
}
function close(restore = false) {
  if (!opened.value) return
  opened.value = false
  query.value = ''
  prefix = ''
  active.value = -1
  detach()
  if (restore) trigger.value?.focus({ preventScroll: true })
}
function choose(index: number) {
  const option = matches.value[index]
  if (!option || option.disabled || props.disabled) return
  close(true)
  if (option.value !== props.value) {
    emit('update:value', option.value)
    emit('change', option.value)
  }
}
function clear() {
  close()
  trigger.value?.focus({ preventScroll: true })
  emit('update:value', undefined)
}
function search(event: Event) {
  if (composing.value || (event as InputEvent).isComposing) return
  query.value = (event.target as HTMLInputElement).value
  open()
}
function endComposition(event: CompositionEvent) { composing.value = false; search(event) }

function onKey(event: KeyboardEvent) {
  if (props.disabled || composing.value || event.isComposing || event.keyCode === 229 || event.defaultPrevented) return
  const key = event.key
  if (key === 'Tab') { close(); return }
  if (key === 'Escape' && opened.value) {
    event.preventDefault()
    event.stopPropagation()
    close(true)
  } else if (key === 'ArrowDown' || key === 'ArrowUp') {
    event.preventDefault()
    event.stopPropagation()
    if (!opened.value) open(key === 'ArrowUp')
    else {
      const list = available.value
      if (list.length) {
        const at = list.indexOf(active.value)
        const next = at < 0 ? (key === 'ArrowDown' ? 0 : list.length - 1) : (at + (key === 'ArrowDown' ? 1 : -1) + list.length) % list.length
        setActive(list[next]!)
      }
    }
  } else if (opened.value && (key === 'Home' || key === 'End') && !event.shiftKey && !event.ctrlKey && !event.metaKey) {
    event.preventDefault()
    setActive((key === 'Home' ? available.value[0] : available.value[available.value.length - 1]) ?? -1)
  } else if ((key === 'Enter' && (opened.value || !props.searchable)) || (key === ' ' && !props.searchable)) {
    event.preventDefault()
    event.stopPropagation()
    if (opened.value) choose(active.value)
    else open()
  } else if (!props.searchable && key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
    const now = performance.now()
    prefix = (now - prefixAt < 700 ? prefix : '') + key.toLocaleLowerCase()
    prefixAt = now
    open()
    const i = matches.value.findIndex(option => !option.disabled && option.label.toLocaleLowerCase().startsWith(prefix))
    if (i >= 0) { event.preventDefault(); setActive(i) }
  }
}
function outside(event: Event) {
  const target = event.target as Node | null
  if (!anchor.value?.contains(target) && !popup.value?.contains(target)) close()
}
function scrollOutside(event: Event) { if (!(event.target instanceof Node) || !popup.value?.contains(event.target)) close() }
function resize() { close() }
function attach() {
  document.addEventListener('pointerdown', outside, true)
  document.addEventListener('focusin', outside, true)
  window.addEventListener('scroll', scrollOutside, true)
  window.addEventListener('resize', resize)
  window.visualViewport?.addEventListener('resize', resize)
}
function detach() {
  document.removeEventListener('pointerdown', outside, true)
  document.removeEventListener('focusin', outside, true)
  window.removeEventListener('scroll', scrollOutside, true)
  window.removeEventListener('resize', resize)
  window.visualViewport?.removeEventListener('resize', resize)
}
watch(() => props.disabled, disabled => { if (disabled) close() })
watch([matches, () => props.value], () => {
  if (!opened.value) return
  place()
  const selected = matches.value.findIndex(option => !option.disabled && option.value === props.value)
  setActive(selected >= 0 ? selected : available.value[0] ?? -1)
})
onDeactivated(() => close())
onBeforeUnmount(detach)
</script>

<template>
  <div ref="anchor" class="v10-choice" :class="{ 'v10-choice-open': opened }">
    <input v-if="searchable" ref="trigger" class="v10-choice-trigger" v-bind="description" aria-autocomplete="list"
      :value="query" :placeholder="label ?? placeholder ?? '请选择'" :class="{ 'v10-choice-placeholder': !label }"
      autocomplete="off" @click="open()" @input="search" @keydown="onKey" @compositionstart="composing = true" @compositionend="endComposition" />
    <button v-else ref="trigger" class="v10-choice-trigger" type="button" v-bind="description"
      @click="opened ? close() : open()" @keydown="onKey"><span>{{ label ?? placeholder ?? '请选择' }}</span></button>
    <button v-if="allowClear && value !== undefined" class="v10-choice-clear" type="button" :disabled="disabled"
      :aria-label="ariaLabel ? '清除' + ariaLabel : '清除选择'" @click="clear"><CloseOutlined /></button>
    <span v-else class="v10-choice-cue" aria-hidden="true">选择</span>
    <Teleport to="body">
      <ul v-if="opened" :id="listId" ref="popup" class="v10-choice-popup" role="listbox" :aria-label="ariaLabel || label || placeholder || '可选项'" :style="position">
        <li v-for="(option, i) in matches" :id="optionId(i)" :key="option.value" role="option"
          :aria-selected="option.value === value" :aria-disabled="option.disabled || undefined" :data-active="active === i"
          @mousedown.prevent @pointermove="!option.disabled && active !== i && setActive(i)" @click="choose(i)">
          <span>{{ option.label }}</span><CheckOutlined v-if="option.value === value" aria-hidden="true" />
        </li>
        <li v-if="!matches.length" class="v10-choice-empty" role="presentation">没有匹配选项</li>
      </ul>
    </Teleport>
  </div>
</template>
