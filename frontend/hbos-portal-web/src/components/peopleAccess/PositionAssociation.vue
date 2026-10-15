<template>
  <a-modal :open="true" :title="confirming ? '确认岗位关联变更' : '关联岗位'" :width="750" :footer="null" :mask-closable="false" wrap-class-name="iam-modal" @cancel="$emit('close')">
    <div class="iam-readonly-line"><span>当前角色</span><strong>{{ role.name }}</strong></div>
    <template v-if="confirming">
      <p class="iam-note">以下 {{ changes.changed.length }} 个岗位的角色关联将变化，涉及 {{ changes.affected.length }} 名演示人员。</p>
      <div class="iam-table-wrap"><table class="iam-table iam-scope-table" aria-label="岗位关联变化"><thead><tr><th scope="col">部门 / 岗位</th><th scope="col">变化</th><th scope="col">范围</th></tr></thead><tbody><tr v-for="position in changes.changed" :key="position.id"><td>{{ demo.departmentName(position.departmentId) }} / {{ position.name }}</td><td>{{ selected.includes(position.id) ? '关联角色' : '解除关联' }}</td><td>{{ position.scopeLabel }}</td></tr></tbody></table></div>
      <p class="iam-note">正式系统须核验变更资格及所需审批。本页仅演示关联结果。</p>
    </template>
    <template v-else>
      <p class="iam-note">勾选要关联的部门岗位。任职于这些岗位的人员将显示该角色，具体数据范围沿用各岗位设置。</p>
      <div class="iam-table-wrap" tabindex="0" aria-label="岗位关联表，可横向滚动"><table class="iam-table iam-mapping-table" aria-label="岗位关联"><thead><tr><th scope="col">选择</th><th scope="col">部门</th><th scope="col">岗位</th><th scope="col">数据范围</th><th scope="col">人数</th></tr></thead><tbody><tr v-for="position in demo.data.positions" :key="position.id"><td><input v-model="selected" type="checkbox" :value="position.id" :aria-label="'关联 ' + demo.departmentName(position.departmentId) + ' ' + position.name" /></td><td>{{ demo.departmentName(position.departmentId) }}</td><td>{{ position.name }}</td><td>{{ position.scopeLabel }}</td><td>{{ demo.positionCount(position.id) }}</td></tr></tbody></table></div>
      <p class="iam-note">部门、岗位及其范围后续由组织架构模块维护。</p>
    </template>
    <p v-if="error" class="iam-validation" role="alert">{{ error }}</p>
    <div class="iam-modal-footer"><small>仅保存本次演示，刷新恢复</small><button type="button" class="iam-btn" @click="confirming ? confirming = false : $emit('close')">{{ confirming ? '返回修改' : '取消' }}</button><button type="button" class="iam-btn iam-primary" @click="save">{{ confirming ? '确认变更' : '保存' }}</button></div>
  </a-modal>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DemoRole } from '@/contracts/peopleAccessDemo'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
const props = defineProps<{ role: DemoRole }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const demo = usePeopleAccessDemoStore()
const selected = ref(demo.data.positions.filter(position => position.roleIds.includes(props.role.id)).map(position => position.id))
const confirming = ref(false), error = ref('')
const changes = computed(() => demo.mappingChanges(props.role.id, selected.value))
function save() {
  if (!confirming.value && changes.value.changed.length) { confirming.value = true; return }
  try { demo.saveMapping(props.role.id, selected.value); emit('saved') }
  catch (cause) { error.value = (cause as Error).message }
}
</script>
