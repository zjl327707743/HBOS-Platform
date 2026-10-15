<template>
  <a-modal :open="true" :title="confirming ? '确认任职变更' : person ? '编辑人员' : '新增人员'" :width="620" :footer="null" :mask-closable="false" wrap-class-name="iam-modal" @cancel="$emit('close')">
    <template v-if="confirming">
      <p class="iam-note">请核对岗位及关联角色的变化。本次仅演示页面效果。</p>
      <h3 class="iam-section-label">变更前 · {{ person?.active ? '启用' : '停用' }}</h3>
      <AssignmentSummary :position-ids="person?.positionIds || []" />
      <h3 class="iam-section-label">变更后 · {{ draft.active ? '启用' : '停用' }}</h3>
      <AssignmentSummary :position-ids="draft.positionIds" />
      <p class="iam-note">正式生效须核验任职、业务范围及所需审批。</p>
    </template>
    <form v-else id="iam-person-form" class="iam-form-grid" @submit.prevent="submit">
      <label class="iam-field"><span>ID</span><input :value="draft.id" readonly /></label>
      <label class="iam-field"><span><i>*</i>人员名称</span><input v-model="draft.name" maxlength="30" placeholder="请输入人员名称" /></label>
      <label class="iam-field"><span><i>*</i>手机号</span><input v-model="draft.phone" maxlength="11" placeholder="演示可用 138****2999" /></label>
      <label class="iam-field"><span>人员状态</span><select v-model="draft.active"><option :value="true">启用</option><option :value="false">停用</option></select></label>
      <div class="iam-field iam-full"><span>部门与岗位</span>
        <div v-for="(id, index) in draft.positionIds" :key="index" class="iam-position-card">
          <div class="iam-position-title"><span>{{ index ? '兼任岗位 ' + index : '主岗' }}</span><button v-if="index" type="button" class="iam-text-btn" @click="removeAssignment(index)">移除</button></div>
          <div class="iam-form-grid">
            <label class="iam-field"><span>部门</span><select v-model="departmentIds[index]" :aria-label="'部门 ' + (index + 1)" @change="draft.positionIds[index] = ''"><option value="">请选择部门</option><option v-for="department in editableDepartments" :key="department.id" :value="department.id">{{ department.name }}</option></select></label>
            <label class="iam-field"><span>岗位</span><select v-model="draft.positionIds[index]" :aria-label="'岗位 ' + (index + 1)"><option value="">请选择岗位</option><option v-for="position in demo.data.positions.filter(item => item.departmentId === departmentIds[index])" :key="position.id" :value="position.id">{{ position.name }}</option></select></label>
          </div>
        </div>
        <button type="button" class="iam-text-btn iam-add-assignment" @click="draft.positionIds.push(''); departmentIds.push('')"><PlusOutlined />添加兼任岗位</button>
      </div>
      <div class="iam-field iam-full"><span>关联角色</span><div class="iam-derived"><p class="iam-note">由所选岗位自动关联</p><AssignmentSummary :position-ids="draft.positionIds" /></div></div>
    </form>
    <p v-if="error" class="iam-validation" role="alert">{{ error }}</p>
    <div class="iam-modal-footer"><small>仅保存本次演示，刷新恢复</small><button type="button" class="iam-btn" @click="confirming ? confirming = false : $emit('close')">{{ confirming ? '返回修改' : '取消' }}</button><button type="button" class="iam-btn iam-primary" @click="confirming ? commit() : submit()">{{ confirming ? '确认变更' : '保存' }}</button></div>
  </a-modal>
</template>
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { DemoPerson } from '@/contracts/peopleAccessDemo'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
import AssignmentSummary from './AssignmentSummary.vue'
const props = defineProps<{ person?: DemoPerson }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const demo = usePeopleAccessDemoStore()
const draft = reactive<DemoPerson>(props.person ? { ...props.person, positionIds: [...props.person.positionIds] } : { id: demo.nextPersonId(), name: '', phone: '', active: true, positionIds: [''] })
const departmentIds = ref(draft.positionIds.map(id => demo.data.positions.find(item => item.id === id)?.departmentId || ''))
const editableDepartments = computed(() => demo.data.departments.filter(department => demo.data.positions.some(position => position.departmentId === department.id)))
const confirming = ref(false), error = ref('')
function removeAssignment(index: number) { draft.positionIds.splice(index, 1); departmentIds.value.splice(index, 1) }
function submit() {
  error.value = ''
  try {
    demo.validatePerson(draft)
    if (props.person && (props.person.positionIds.join() !== draft.positionIds.join() || props.person.active !== draft.active)) confirming.value = true
    else commit()
  } catch (cause) { error.value = (cause as Error).message }
}
function commit() {
  try { demo.savePerson(draft, props.person?.id); emit('saved') }
  catch (cause) { error.value = (cause as Error).message }
}
</script>
