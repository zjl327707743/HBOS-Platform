<template>
  <a-modal :open="true" :title="role ? '编辑角色' : '添加角色'" :width="750" :footer="null" :mask-closable="false" wrap-class-name="iam-modal" @cancel="$emit('close')">
    <form id="iam-role-form" class="iam-form-grid" @submit.prevent="save">
      <label class="iam-field iam-full"><span><i>*</i>角色名称</span><input v-model="name" maxlength="30" placeholder="请输入角色名称" /></label>
      <label class="iam-field iam-full"><span>角色描述</span><textarea v-model="description" maxlength="200" placeholder="请输入角色描述"></textarea></label>
    </form>
    <div class="iam-editor-tabs" role="tablist" aria-label="角色配置">
      <button id="iam-permissions-tab" type="button" role="tab" :aria-selected="tab === 'permissions'" aria-controls="iam-role-panel" :class="{ active: tab === 'permissions' }" @click="tab = 'permissions'">菜单与操作权限</button>
      <button id="iam-scope-tab" type="button" role="tab" :aria-selected="tab === 'scope'" aria-controls="iam-role-panel" :class="{ active: tab === 'scope' }" @click="tab = 'scope'">关联岗位与范围</button>
    </div>
    <div id="iam-role-panel" class="iam-permissions-box" role="tabpanel" :aria-labelledby="tab === 'permissions' ? 'iam-permissions-tab' : 'iam-scope-tab'">
      <template v-if="tab === 'permissions'">
        <div class="iam-permission-tools"><span>勾选角色可使用的菜单与操作</span><input v-model="query" aria-label="搜索菜单权限" placeholder="搜索菜单 / 功能" /></div>
        <details v-for="app in filteredDirectory" :key="app.id" class="iam-permission-app" open>
          <summary>{{ app.label }}</summary>
          <div v-for="menu in app.menus" :key="menu.id" class="iam-permission-row">
            <label class="iam-check"><input type="checkbox" :checked="allSelected(menu)" :indeterminate="partSelected(menu)" :aria-label="'选择 ' + menu.label + ' 的全部操作'" @change="toggleMenu(menu, ($event.target as HTMLInputElement).checked)" />{{ menu.label }}</label>
            <div class="iam-permission-actions"><label v-for="action in menu.actions" :key="action.id" class="iam-check"><input v-model="selected" type="checkbox" :value="action.id" :aria-label="menu.label + ' ' + action.label" />{{ action.label }}</label></div>
          </div>
        </details>
        <p v-if="!filteredDirectory.length" class="iam-note">未找到匹配的菜单与操作</p>
      </template>
      <template v-else>
        <p class="iam-note">角色定义可执行的操作。具体业务范围由关联岗位确定。</p>
        <div class="iam-table-wrap"><table class="iam-table iam-scope-table" aria-label="角色关联的岗位与范围"><thead><tr><th scope="col">部门</th><th scope="col">岗位</th><th scope="col">具体数据范围</th></tr></thead><tbody><tr v-for="position in linkedPositions" :key="position.id"><td>{{ demo.departmentName(position.departmentId) }}</td><td>{{ position.name }}</td><td>{{ position.scopeLabel }}</td></tr><tr v-if="!linkedPositions.length"><td colspan="3" class="iam-empty">暂无关联岗位，可在保存角色后配置</td></tr></tbody></table></div>
        <p class="iam-note">岗位维护后可继续关联角色；新增功能不会自动勾选。</p>
      </template>
    </div>
    <p class="iam-note iam-permission-count" role="status">已选择 {{ selected.length }} 项操作权限 · 示例目录支持后续业务模块扩充</p>
    <p v-if="error" class="iam-validation" role="alert">{{ error }}</p>
    <div class="iam-modal-footer"><small>仅保存本次演示，刷新恢复</small><button type="button" class="iam-btn" @click="$emit('close')">取消</button><button type="button" class="iam-btn iam-primary" @click="save">保存</button></div>
  </a-modal>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DemoMenu, DemoRole } from '@/contracts/peopleAccessDemo'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
const props = defineProps<{ role?: DemoRole }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const demo = usePeopleAccessDemoStore()
const name = ref(props.role?.name || ''), description = ref(props.role?.description || '')
const selected = ref([...(props.role?.permissionIds || [])]), query = ref(''), tab = ref('permissions'), error = ref('')
const linkedPositions = computed(() => demo.data.positions.filter(position => props.role && position.roleIds.includes(props.role.id)))
const filteredDirectory = computed(() => demo.data.directory.map(app => ({ ...app, menus: app.menus.filter(menu =>
  `${app.label} ${menu.label}`.includes(query.value.trim())) })).filter(app => app.menus.length))
const allSelected = (menu: DemoMenu) => menu.actions.length > 0 && menu.actions.every(action => selected.value.includes(action.id))
const partSelected = (menu: DemoMenu) => !allSelected(menu) && menu.actions.some(action => selected.value.includes(action.id))
function toggleMenu(menu: DemoMenu, checked: boolean) {
  const ids = new Set(selected.value)
  for (const action of menu.actions) { if (checked) ids.add(action.id); else ids.delete(action.id) }
  selected.value = [...ids]
}
function save() {
  error.value = ''
  try { demo.saveRole({ name: name.value, description: description.value, permissionIds: selected.value }, props.role?.id); emit('saved') }
  catch (cause) { error.value = (cause as Error).message }
}
</script>
