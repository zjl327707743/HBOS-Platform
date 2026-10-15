<template>
  <div class="iam-page">
    <div class="iam-page-heading"><div><h1>人员与权限</h1><p>查看人员资料、原生角色与岗位任职</p></div><span class="iam-version">当前站点 · 只读</span></div>
    <nav class="iam-page-tabs" aria-label="人员与权限页面"><RouterLink to="/hbos/admin/people">人员信息</RouterLink><RouterLink to="/hbos/admin/roles">权限管理</RouterLink><span>组织岗位 → 角色权限 → 人员任职</span></nav>
    <div v-if="isPeople" class="iam-person-layout">
      <aside class="iam-panel iam-org" aria-label="组织架构">
        <h2 class="iam-panel-title">组织架构</h2>
        <label class="iam-org-search"><SearchOutlined /><input v-model="orgQuery" aria-label="搜索组织" placeholder="搜索组织名称" /></label>
        <div class="iam-org-tree">
          <button class="iam-tree-btn" :class="{ selected: !department }" @click="chooseDepartment('')"><FolderFilled />全部可查看人员</button>
          <button v-for="item in visibleDepartments" :key="item.id" class="iam-tree-btn" :class="{ selected: department === item.id }" :disabled="source !== 'Employee'" @click="chooseDepartment(item.id)"><FolderFilled /><span>{{ item.name }}</span></button>
        </div>
        <p v-if="orgError" class="iam-note" role="status">{{ orgError }}</p>
        <p v-if="orgTruncated" class="iam-note">组织列表仅显示前 200 项，请直接选择具体部门。</p>
        <p class="iam-org-foot">组织名称来自当前站点<br />部门筛选适用于员工资料，当前仅筛选所选部门</p>
      </aside>
      <section class="iam-panel iam-workspace" aria-label="人员信息列表">
        <h2 class="iam-panel-title">人员信息<span class="iam-right-note">{{ source === 'User' ? '账号资料' : '员工资料' }}</span></h2>
        <form class="iam-toolbar" @submit.prevent="search">
          <select v-model="source" aria-label="资料来源" @change="switchSource"><option value="User">账号资料</option><option value="Employee">员工资料</option></select>
          <input v-model="draftName" aria-label="人员名称筛选" placeholder="请输入人员名称" />
          <input v-model="draftPosition" :disabled="source !== 'Employee'" aria-label="岗位筛选" placeholder="请输入岗位名称" />
          <button class="iam-btn iam-primary" :disabled="loading" type="submit"><SearchOutlined />搜索</button><button class="iam-btn" type="button" @click="reset">重置</button>
          <div class="iam-toolbar-push"><button class="iam-btn iam-primary" type="button" disabled title="人员资料写入尚未接入"><PlusOutlined />新增人员</button></div>
        </form>
        <p class="iam-note">{{ source === 'User' ? '显示当前账号资料；员工部门及岗位任职尚待关联。' : '部门和岗位来自员工资料；具体岗位授权关系尚未接入。' }} 手机号仅脱敏显示；岗位派生角色与授权变更暂未开放。</p>
        <p v-if="error" class="iam-note" role="alert">{{ error }} <button class="iam-text-btn" @click="load">重试</button></p>
        <div class="iam-table-wrap" tabindex="0" aria-label="人员信息表，可横向滚动"><table class="iam-table" aria-label="人员信息">
          <thead><tr><th v-for="column in ['ID', '人员名称', '部门', '岗位', '手机号', '角色', '操作']" :key="column" scope="col">{{ column }}</th></tr></thead>
          <tbody><tr v-for="person in people" :key="person.id" :class="{ 'iam-inactive': !person.active }">
            <td class="iam-id">{{ person.display_id }}</td><td class="iam-person-name">{{ person.name }}<small v-if="!person.active">（停用）</small></td><td>{{ person.department || '未关联' }}</td><td>{{ person.position || '未关联' }}</td><td>{{ person.phone || '—' }}</td>
            <td><span v-if="person.role_profile" class="iam-role-tag" title="现有原生角色配置，不代表带范围的岗位授权">{{ person.role_profile }}</span><span v-else class="iam-muted">岗位角色待接入</span></td>
            <td><div class="iam-actions"><button class="iam-text-btn" disabled title="人员编辑尚未接入"><EditOutlined />编辑</button><button class="iam-text-btn" @click="detail = person">详情</button></div></td>
          </tr><tr v-if="!people.length"><td colspan="7" class="iam-empty">{{ loading ? '正在读取人员资料…' : error ? '人员资料暂不可用' : '暂无可查看的人员资料' }}</td></tr></tbody>
        </table></div>
        <a-pagination v-model:current="page" v-model:page-size="pageSize" class="iam-pagination" :total="total" :show-size-changer="true" :page-size-options="['10', '20', '50']" :show-total="(n: number) => `共 ${n} 条`" size="small" />
      </section>
    </div>
    <section v-else class="iam-panel iam-roles" aria-label="权限管理列表">
      <h2 class="iam-panel-title">权限管理<span class="iam-right-note">当前站点的原生角色</span></h2>
      <form class="iam-toolbar" @submit.prevent="search"><input v-model="draftName" aria-label="角色名称筛选" placeholder="请输入角色名称" /><button class="iam-btn iam-primary" :disabled="loading" type="submit"><SearchOutlined />搜索</button><button class="iam-btn" type="button" @click="reset">重置</button><div class="iam-toolbar-push"><button class="iam-btn" type="button" @click="positionsOpen = true">查看岗位</button><button class="iam-btn iam-primary" type="button" disabled title="角色授权写入尚未接入"><PlusOutlined />添加角色</button></div></form>
      <p v-if="error" class="iam-note" role="alert">{{ error }} <button class="iam-text-btn" @click="load">重试</button></p>
      <div class="iam-table-wrap" tabindex="0" aria-label="权限管理表，可横向滚动"><table class="iam-table iam-role-table" aria-label="角色权限"><thead><tr><th v-for="column in ['序号', '角色', '创建时间', '描述', '操作']" :key="column" scope="col">{{ column }}</th></tr></thead><tbody>
        <tr v-for="(role, index) in roles" :key="role.id"><td>{{ (page - 1) * pageSize + index + 1 }}</td><td class="iam-person-name">{{ role.name }}</td><td>{{ role.created_at.slice(0, 10) || '—' }}</td><td>{{ role.description }}</td><td><div class="iam-actions"><button class="iam-text-btn" disabled title="角色编辑尚未接入">编辑</button><button class="iam-text-btn" disabled title="岗位授权关联尚未接入">关联岗位</button><button class="iam-text-btn" disabled title="真实角色不可在此删除">删除</button></div></td></tr>
        <tr v-if="!roles.length"><td colspan="5" class="iam-empty">{{ loading ? '正在读取角色…' : error ? '角色资料暂不可用' : '暂无可查看的角色' }}</td></tr>
      </tbody></table></div>
      <a-pagination v-model:current="page" v-model:page-size="pageSize" class="iam-pagination" :total="total" :show-size-changer="true" :page-size-options="['10', '20', '50']" :show-total="(n: number) => `共 ${n} 条`" size="small" />
      <p class="iam-footnote">角色来自当前 Frappe 站点。固定版本、业务范围与岗位关联尚未接入，当前页面只读。</p>
    </section>
    <a-modal v-if="detail" :open="true" title="人员详情" :width="620" :footer="null" wrap-class-name="iam-modal" @cancel="detail = undefined">
      <div class="iam-detail-heading"><span class="iam-avatar">{{ detail.name.slice(-1) }}</span><div><strong>{{ detail.name }}</strong><small>{{ detail.display_id }}</small></div><span class="iam-role-tag">{{ detail.active ? '启用' : '停用' }}</span></div>
      <p class="iam-note">部门：{{ detail.department || '未关联' }} · 岗位：{{ detail.position || '未关联' }}</p><p class="iam-note">手机号：{{ detail.phone || '—' }} · 账号：{{ detail.account_linked ? '已关联' : '未关联' }}</p><p class="iam-note">账号角色来自原生资料，不代表岗位授权。</p>
      <ManagedOrganizationReadOnly v-if="source === 'Employee'" :key="detail.record_id" kind="assignments" :employee-id="detail.record_id" />
      <p v-else class="iam-note">当前为账号资料，关联员工后方可查询任职。</p>
      <div class="iam-modal-footer"><button class="iam-btn" @click="detail = undefined">关闭</button></div>
    </a-modal>
    <a-modal v-if="positionsOpen" :open="true" title="具体岗位 · 只读" :width="950" :footer="null" wrap-class-name="iam-modal" @cancel="positionsOpen = false">
      <ManagedOrganizationReadOnly kind="positions" />
      <div class="iam-modal-footer"><button class="iam-btn" @click="positionsOpen = false">关闭</button></div>
    </a-modal>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { EditOutlined, FolderFilled, PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { getPeople, getPeopleOrganizations, getPeopleRoles, type LiveDepartment, type LivePerson, type LiveRole, type PersonnelSource } from '@/services/peopleAccessApi'
import { portalErrorMessage } from '@/services/portalErrors'
import ManagedOrganizationReadOnly from '@/components/peopleAccess/ManagedOrganizationReadOnly.vue'
import '@/styles/peopleAccess.css'
const route = useRoute(), isPeople = computed(() => route.name === 'admin-people')
const source = ref<PersonnelSource>('User'), people = ref<LivePerson[]>([]), roles = ref<LiveRole[]>([]), departments = ref<LiveDepartment[]>([])
const page = ref(1), pageSize = ref(10), total = ref(0), loading = ref(false), error = ref(''), orgError = ref(''), orgTruncated = ref(false)
const draftName = ref(''), draftPosition = ref(''), name = ref(''), position = ref(''), department = ref(''), orgQuery = ref(''), detail = ref<LivePerson>()
const visibleDepartments = computed(() => departments.value.filter(item => item.name.includes(orgQuery.value.trim())))
const positionsOpen = ref(false)
let generation = 0, alive = true
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''; people.value = []; roles.value = []; total.value = 0; detail.value = undefined
  try {
    if (isPeople.value) {
      const result = await getPeople({ source: source.value, page: page.value, page_size: pageSize.value, name: name.value, department: department.value, position: position.value })
      if (alive && current === generation) { people.value = result.items; total.value = result.total }
    } else {
      const result = await getPeopleRoles(page.value, pageSize.value, name.value)
      if (alive && current === generation) { roles.value = result.items; total.value = result.total }
    }
  } catch (cause) { if (alive && current === generation) error.value = portalErrorMessage(cause, '资料读取失败，请稍后重试。') }
  finally { if (alive && current === generation) loading.value = false }
}
function refreshFromStart() { if (page.value === 1) void load(); else page.value = 1 }
function search() { name.value = draftName.value.trim(); position.value = source.value === 'Employee' ? draftPosition.value.trim() : ''; refreshFromStart() }
function reset() { detail.value = undefined; draftName.value = draftPosition.value = name.value = position.value = department.value = orgQuery.value = ''; refreshFromStart() }
function switchSource() { reset() }
function chooseDepartment(value: string) { department.value = value; refreshFromStart() }
watch([page, pageSize], () => { void load() })
watch(isPeople, () => { positionsOpen.value = false; reset() })
onMounted(() => { void load(); void getPeopleOrganizations().then(result => { if (alive) { departments.value = result.items; orgTruncated.value = result.truncated } }).catch(cause => { if (alive) orgError.value = portalErrorMessage(cause, '组织资料暂不可用。') }) })
onUnmounted(() => { alive = false; generation += 1 })
</script>
