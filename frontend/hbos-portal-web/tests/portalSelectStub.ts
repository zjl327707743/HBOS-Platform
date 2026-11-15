import { defineComponent } from 'vue'

export const portalSelectStub = defineComponent({
  props: ['value', 'options', 'disabled', 'placeholder', 'searchable'],
  emits: ['update:value', 'change'],
  template: `<select :value="value" :disabled="disabled" @change="select">
    <option v-for="item in options" :key="item.value" :value="item.value">{{ item.label }}</option>
  </select>`,
  methods: {
    select(event: Event) {
      const select = event.target as HTMLSelectElement
      const value = this.options[select.selectedIndex]?.value
      this.$emit('update:value', value)
      this.$emit('change', value)
    },
  },
})
