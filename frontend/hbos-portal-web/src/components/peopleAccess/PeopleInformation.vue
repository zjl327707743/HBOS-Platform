<template>
  <div class="iam-person-layout">
    <aside class="iam-panel iam-org" aria-label="组织架构">
      <h2 class="iam-panel-title">组织架构</h2>
      <label class="iam-org-search"><SearchOutlined /><input v-model="organizationQuery" aria-label="搜索组织" placeholder="搜索组织名称" /></label>
      <div class="iam-org-tree">
        <button v-for="department in demo.data.departments.filter(item => item.name.includes(organizationQuery.trim()))" :key="department.id" type="button" class="iam-tree-btn" :class="{ selected: filter.departmentId === department.id }" :style="{ paddingLeft: department.level * 13 + 6 + 'px' }" :aria-pressed="filter.departmentId === department.id" @click="filter.departmentId = department.id; page = 1">
          <span class="iam-chevron">{{ ['all', 'qc'].includes(department.id) ? '▾' : '' }}</span><FolderFilled /><span>{{ department.name }}</span><small>{{ demo.departmentCount(department.id) }}</small>
        </button>
        <p v-if="!demo.data.departments.some(item => item.name.includes(organizationQuery.trim()))" class="iam-note">未找到组织</p>
      </div>
      <p class="iam-org-foot">组织与岗位将在后续统一维护<br />此处用于筛选人员与查看任职</p>
    </aside>
    <section class="iam-panel iam-workspace" aria-label="人员信息列表">
      <h2 class="iam-panel-title">人员信息<small>{{ demo.departmentName(filter.departmentId) }}</small><span class="iam-right-note">角色随岗位关联</span></h2>
      <form class="iam-toolbar" @submit.prevent="search">
        <input v-model="searchDraft.name" aria-label="人员名称筛选" placeholder="请输入人员名称" />
        <input v-model="searchDraft.phone" aria-label="手机号筛选" placeholder="请输入手机号" />
        <select v-model="searchDraft.position" aria-label="岗位筛选"><option value="">全部岗位</option><option v-for="name in positionNames" :key="name">{{ name }}</option></select>
        <select v-model="searchDraft.roleId" aria-label="角色筛选"><option value="">全部角色</option><option v-for="role in demo.data.roles" :key="role.id" :value="role.id">{{ role.name }}</option></select>
        <button class="iam-btn iam-primary" type="submit"><SearchOutlined />搜索</button><button class="iam-btn" type="button" @click="reset">重置</button>
        <div class="iam-toolbar-push"><label class="iam-check"><input v-model="filter.includeChildren" type="checkbox" @change="page = 1" />包含下级</label><button class="iam-btn iam-primary" type="button" @click="openEditor()"><PlusOutlined />新增人员</button></div>
      </form>
      <div class="iam-table-wrap" tabindex="0" aria-label="人员信息表，可横向滚动">
        <table class="iam-table" aria-label="人员信息"><colgroup><col style="width:9%" /><col style="width:11%" /><col style="width:15%" /><col style="width:15%" /><col style="width:15%" /><col style="width:19%" /><col style="width:16%" /></colgroup>
          <thead><tr><th v-for="column in ['ID', '人员名称', '部门', '岗位', '手机号', '角色', '操作']" :key="column" scope="col">{{ column }}</th></tr></thead>
          <tbody><tr v-for="person in paged" :key="person.id" :class="{ 'iam-inactive': !person.active }">
            <td class="iam-id">{{ person.id }}</td><td class="iam-person-name">{{ person.name }}<small v-if="!person.active">（停用）</small></td>
            <td><div v-for="id in [...new Set(demo.personPositions(person).map(item => item.departmentId))]" :key="id">{{ demo.departmentName(id) }}</div></td>
            <td><div v-for="(position, index) in demo.personPositions(person)" :key="position.id">{{ position.name }}<small v-if="index" class="iam-muted"> 兼任</small></div></td>
            <td>{{ person.phone }}</td><td><div class="iam-tags"><span v-for="role in demo.personRoles(person)" :key="role.id" class="iam-role-tag">{{ role.name }}</span><span v-if="!demo.personRoles(person).length" class="iam-muted">未关联角色</span></div></td>
            <td><div class="iam-actions"><button type="button" class="iam-text-btn" :aria-label="'编辑 ' + person.name" @click="openEditor(person)"><EditOutlined />编辑</button><button type="button" class="iam-text-btn" :aria-label="'详情 ' + person.name" @click="detail = person">详情</button></div></td>
          </tr><tr v-if="!filtered.length"><td colspan="7" class="iam-empty">暂无符合条件的人员，请调整筛选条件。</td></tr></tbody>
        </table>
      </div>
      <a-pagination v-model:current="page" v-model:page-size="pageSize" class="iam-pagination" :total="filtered.length" :page-size-options="['5', '10', '20']" :show-size-changer="true" :show-total="(total: number) => `共 ${total} 条`" size="small" />
    </section>
    <PersonEditor v-if="editing" :person="selected" @close="editing = false" @saved="editing = false; message.success('人员信息已在演示中更新')" />
    <a-modal v-if="detail" :open="true" title="人员详情" :width="620" :footer="null" wrap-class-name="iam-modal" @cancel="detail = undefined">
      <div class="iam-detail-heading"><span class="iam-avatar">{{ detail.name.slice(-1) }}</span><div><strong>{{ detail.name }}</strong><small>{{ detail.id }}</small></div><span class="iam-role-tag">{{ detail.active ? '启用' : '停用' }}</span></div>
      <p class="iam-note">手机号：{{ detail.phone }} · 任职数量：{{ detail.positionIds.length }} 个岗位</p>
      <h3 class="iam-section-label">岗位与权限来源</h3><AssignmentSummary :position-ids="detail.positionIds" show-scope />
      <p class="iam-note">角色按每条任职与范围分别匹配，兼任不会合并扩大业务范围。</p>
      <div class="iam-modal-footer"><button type="button" class="iam-btn" @click="detail = undefined">关闭</button><button type="button" class="iam-btn iam-primary" @click="openEditor(detail); detail = undefined">编辑人员</button></div>
    </a-modal>
  </div>
</template>
<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { EditOutlined, FolderFilled, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { DemoPerson, DemoPersonFilter } from '@/contracts/peopleAccessDemo'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
import PersonEditor from './PersonEditor.vue'
import AssignmentSummary from './AssignmentSummary.vue'
const demo = usePeopleAccessDemoStore()
const emptySearch = () => ({ name: '', phone: '', position: '', roleId: '' })
const searchDraft = reactive(emptySearch())
const filter = reactive<DemoPersonFilter>({ ...emptySearch(), departmentId: 'all', includeChildren: true })
const organizationQuery = ref(''), page = ref(1), pageSize = ref(10)
const editing = ref(false), selected = ref<DemoPerson>(), detail = ref<DemoPerson>()
const positionNames = computed(() => [...new Set(demo.data.positions.map(item => item.name))])
const filtered = computed(() => demo.filterPeople(filter))
const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))
watch([() => filtered.value.length, pageSize], () => { page.value = Math.min(page.value, Math.max(1, Math.ceil(filtered.value.length / pageSize.value))) })
function search() { Object.assign(filter, searchDraft, { name: searchDraft.name.trim(), phone: searchDraft.phone.trim() }); page.value = 1 }
function reset() { Object.assign(searchDraft, emptySearch()); Object.assign(filter, emptySearch(), { departmentId: 'all', includeChildren: true }); organizationQuery.value = ''; page.value = 1 }
function openEditor(person?: DemoPerson) { selected.value = person; editing.value = true }
</script>
