<template>
  <section class="iam-panel iam-roles" aria-label="权限管理列表">
    <h2 class="iam-panel-title">权限管理<span class="iam-right-note">配置角色权限，再关联到部门岗位</span></h2>
    <form class="iam-toolbar" @submit.prevent="query = searchDraft.trim(); page = 1"><input v-model="searchDraft" aria-label="角色名称筛选" placeholder="请输入角色名称" /><button type="submit" class="iam-btn iam-primary"><SearchOutlined />搜索</button><button type="button" class="iam-btn" @click="searchDraft = query = ''; page = 1">重置</button><div class="iam-toolbar-push"><button type="button" class="iam-btn iam-primary" @click="openEditor()"><PlusOutlined />添加角色</button></div></form>
    <div class="iam-table-wrap" tabindex="0" aria-label="权限管理表，可横向滚动"><table class="iam-table iam-role-table" aria-label="角色权限"><colgroup><col style="width:65px" /><col style="width:17%" /><col style="width:155px" /><col /><col style="width:235px" /></colgroup><thead><tr><th v-for="column in ['序号', '角色', '创建时间', '描述', '操作']" :key="column" scope="col">{{ column }}</th></tr></thead><tbody><tr v-for="(role, index) in paged" :key="role.id"><td class="iam-id">{{ (page - 1) * pageSize + index + 1 }}</td><td class="iam-person-name">{{ role.name }}</td><td>{{ role.createdAt }}</td><td class="iam-description">{{ role.description }}</td><td><div class="iam-actions"><button type="button" class="iam-text-btn" :aria-label="'编辑角色 ' + role.name" @click="openEditor(role)"><EditOutlined />编辑</button><button type="button" class="iam-text-btn" :aria-label="'关联岗位 ' + role.name" @click="mapping = role">关联岗位</button><button type="button" class="iam-text-btn" :aria-label="'删除角色 ' + role.name" @click="requestDelete(role)"><DeleteOutlined />删除</button></div></td></tr><tr v-if="!filtered.length"><td colspan="5" class="iam-empty">暂无符合条件的角色</td></tr></tbody></table></div>
    <a-pagination v-model:current="page" v-model:page-size="pageSize" class="iam-pagination" :total="filtered.length" :page-size-options="['5', '10', '20']" :show-size-changer="true" :show-total="(total: number) => `共 ${total} 条`" size="small" />
    <p class="iam-footnote">新增岗位可关联已有角色；新增业务功能需单独配置权限。</p>
    <RoleEditor v-if="editing" :role="selected" @close="editing = false" @saved="editing = false; message.success('角色配置已在演示中保存')" />
    <PositionAssociation v-if="mapping" :role="mapping" @close="mapping = undefined" @saved="mapping = undefined; message.success('岗位关联已更新，人员角色同步展示')" />
    <a-modal v-if="deleting" :open="true" title="删除角色" :width="480" :footer="null" wrap-class-name="iam-modal" @cancel="deleting = undefined"><p>确定删除角色“{{ deleting.name }}”？</p><p class="iam-note">仅删除本页的演示角色，刷新可恢复。</p><div class="iam-modal-footer"><button type="button" class="iam-btn" @click="deleting = undefined">取消</button><button type="button" class="iam-btn iam-primary" @click="remove">确认删除</button></div></a-modal>
  </section>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { DemoRole } from '@/contracts/peopleAccessDemo'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
import RoleEditor from './RoleEditor.vue'
import PositionAssociation from './PositionAssociation.vue'
const demo = usePeopleAccessDemoStore()
const searchDraft = ref(''), query = ref(''), page = ref(1), pageSize = ref(10), editing = ref(false)
const selected = ref<DemoRole>(), mapping = ref<DemoRole>(), deleting = ref<DemoRole>()
const filtered = computed(() => demo.data.roles.filter(role => role.name.includes(query.value)))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
watch([() => filtered.value.length, pageSize], () => { page.value = Math.min(page.value, Math.max(1, Math.ceil(filtered.value.length / pageSize.value))) })
function openEditor(role?: DemoRole) { selected.value = role; editing.value = true }
function requestDelete(role: DemoRole) {
  if (demo.data.positions.some(position => position.roleIds.includes(role.id))) { message.warning('该角色已关联岗位，请先解除岗位关联后再删除。'); return }
  deleting.value = role
}
function remove() {
  try { if (deleting.value) demo.deleteRole(deleting.value.id); deleting.value = undefined; message.success('演示角色已删除，刷新可恢复') }
  catch (cause) { message.error((cause as Error).message) }
}
</script>
