import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent } from 'vue'
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
import { checkPortalAccess } from '@/router/portalGuard'
import PersonEditor from '@/components/peopleAccess/PersonEditor.vue'
import RoleEditor from '@/components/peopleAccess/RoleEditor.vue'
import PositionAssociation from '@/components/peopleAccess/PositionAssociation.vue'
import PeopleInformation from '@/components/peopleAccess/PeopleInformation.vue'
import PortalSidebar from '@/components/layout/PortalSidebar.vue'
import MobilePortalNav from '@/components/layout/MobilePortalNav.vue'
import PeopleAccessDemoView from '@/views/PeopleAccessDemoView.vue'

const mode = vi.hoisted(() => ({ value: 'mock' }))
vi.mock('@/services/portalProvider', () => ({ get portalDataSource() { return mode.value } }))
const ModalStub = defineComponent({ props: ['title'], template: '<section :aria-label="title"><slot /></section>' })
const stubs = { 'a-modal': ModalStub, 'a-pagination': true }
const wrappers: ReturnType<typeof mount>[] = []
function button(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper.findAll('button').find(item => item.text() === text)!
}
beforeEach(() => { mode.value = 'mock'; setActivePinia(createPinia()) })
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); vi.restoreAllMocks(); mode.value = 'mock' })

describe('人员与权限前端复刻', () => {
  it('同名岗位按部门区分，兼任角色去重、范围逐条保留、人数去重', () => {
    const demo = usePeopleAccessDemoStore()
    expect(demo.departmentCount('all')).toBe(10)
    expect(demo.departmentCount('lab1')).toBe(4)
    expect(demo.departmentCount('lab2')).toBe(3)
    const concurrent = demo.data.people.find(person => person.id === 'HB010')!
    expect(demo.personRoles(concurrent).map(role => role.id)).toEqual(['r1'])
    expect(demo.personPositions(concurrent).map(position => position.scopeLabel)).toEqual([
      '化验一组 · 本人负责记录（口径待确认）', '无菌检验组 · 本人负责记录（口径待确认）',
    ])
  })
  it('组织包含下级、姓名、手机号、岗位和角色筛选同时生效', () => {
    const demo = usePeopleAccessDemoStore()
    const filter = { departmentId: 'qc', includeChildren: true, name: '', phone: '', position: '', roleId: '' }
    expect(demo.filterPeople(filter)).toHaveLength(6)
    expect(demo.filterPeople({ ...filter, includeChildren: false })).toHaveLength(0)
    expect(demo.filterPeople({ ...filter, name: '张', phone: '2001', position: '检验员', roleId: 'r1' }).map(person => person.id)).toEqual(['HB001'])
    expect(demo.filterPeople({ ...filter, roleId: 'r3' })).toHaveLength(0)
  })
  it('人员编辑在确认前不改变列表，返回修改保留草稿，确认后派生新角色', async () => {
    const demo = usePeopleAccessDemoStore(), person = demo.data.people[0]!
    const wrapper = mount(PersonEditor, { props: { person }, global: { stubs } }); wrappers.push(wrapper)
    await wrapper.get('input[maxlength="30"]').setValue('张明（演示）')
    await wrapper.get('select[aria-label="岗位 1"]').setValue('p2')
    await button(wrapper, '保存').trigger('click')
    expect(wrapper.text()).toContain('变更前')
    expect(wrapper.text()).toContain('检验复核员')
    expect(person.positionIds).toEqual(['p1'])
    await button(wrapper, '返回修改').trigger('click')
    expect((wrapper.get('input[maxlength="30"]').element as HTMLInputElement).value).toBe('张明（演示）')
    expect((wrapper.get('select[aria-label="岗位 1"]').element as HTMLSelectElement).value).toBe('p2')
    await button(wrapper, '保存').trigger('click'); await button(wrapper, '确认变更').trigger('click')
    expect(person.name).toBe('张明（演示）')
    expect(demo.personRoles(person).map(role => role.id)).toEqual(['r2'])
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })
  it('新增人员必填与重复任职校验阻止保存，取消不写入', async () => {
    const demo = usePeopleAccessDemoStore()
    const wrapper = mount(PersonEditor, { global: { stubs } }); wrappers.push(wrapper)
    await button(wrapper, '保存').trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('人员名称')
    expect(demo.data.people).toHaveLength(10)
    expect(() => demo.savePerson({ id: 'unused', name: '演示人员', phone: '138****2999', active: true, positionIds: ['p1', 'p1'] })).toThrow('重复')
    await button(wrapper, '取消').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(demo.data.people).toHaveLength(10)
  })
  it('角色勾选跨搜索和页签保留，取消不改变角色，新功能不自动加入', async () => {
    const demo = usePeopleAccessDemoStore(), role = demo.data.roles[0]!
    const wrapper = mount(RoleEditor, { props: { role }, global: { stubs } }); wrappers.push(wrapper)
    await wrapper.get('input[aria-label="检验记录 提交"]').setValue(false)
    await wrapper.get('input[aria-label="搜索菜单权限"]').setValue('样品')
    await button(wrapper, '关联岗位与范围').trigger('click')
    expect(wrapper.text()).toContain('无菌检验组')
    await button(wrapper, '菜单与操作权限').trigger('click')
    await wrapper.get('input[aria-label="搜索菜单权限"]').setValue('')
    expect((wrapper.get('input[aria-label="检验记录 提交"]').element as HTMLInputElement).checked).toBe(false)
    demo.data.directory[1]!.menus[1]!.actions.push({ id: 'lims.result.export', label: '导出' })
    expect(role.permissionIds).not.toContain('lims.result.export')
    await button(wrapper, '取消').trigger('click')
    expect(role.permissionIds).toContain('lims.result.submit')
    expect(wrapper.emitted('saved')).toBeUndefined()
  })
  it('角色保存拒绝重名和未知功能，新角色从空权限开始', async () => {
    const demo = usePeopleAccessDemoStore()
    const wrapper = mount(RoleEditor, { global: { stubs } }); wrappers.push(wrapper)
    expect(wrapper.text()).toContain('已选择 0 项')
    expect(() => demo.saveRole({ name: '检验员', description: '', permissionIds: [] })).toThrow('已存在')
    expect(() => demo.saveRole({ name: '测试角色', description: '', permissionIds: ['unknown'] })).toThrow('当前目录')
    demo.saveRole({ name: '新增角色', description: '', permissionIds: [] })
    expect(demo.data.roles.at(-1)?.permissionIds).toEqual([])
  })
  it('解除岗位关联只影响选中岗位，确认前不变化，涉及人员去重', async () => {
    const demo = usePeopleAccessDemoStore(), role = demo.data.roles[0]!
    const wrapper = mount(PositionAssociation, { props: { role }, global: { stubs } }); wrappers.push(wrapper)
    await wrapper.get('input[aria-label="关联 无菌检验组 检验员"]').setValue(false)
    await button(wrapper, '保存').trigger('click')
    expect(wrapper.text()).toContain('涉及 3 名演示人员')
    expect(demo.personRoles(demo.data.people[3]!).map(role => role.id)).toEqual(['r1'])
    await button(wrapper, '返回修改').trigger('click')
    expect((wrapper.get('input[aria-label="关联 无菌检验组 检验员"]').element as HTMLInputElement).checked).toBe(false)
    await button(wrapper, '保存').trigger('click'); await button(wrapper, '确认变更').trigger('click')
    expect(demo.personRoles(demo.data.people[3]!)).toEqual([])
    expect(demo.personRoles(demo.data.people[0]!).map(role => role.id)).toEqual(['r1'])
    expect(demo.mappingChanges('r1', []).affected.map(person => person.id)).toEqual(['HB001', 'HB002', 'HB010'])
  })
  it('已关联角色不可删除，解除所有关联后可删除，不产生持久化写入', () => {
    const storage = vi.spyOn(Storage.prototype, 'setItem')
    const network = vi.spyOn(globalThis, 'fetch')
    const demo = usePeopleAccessDemoStore()
    expect(() => demo.deleteRole('r1')).toThrow('先解除')
    demo.saveMapping('r1', []); demo.deleteRole('r1')
    expect(demo.data.roles.some(role => role.id === 'r1')).toBe(false)
    expect(demo.personRoles(demo.data.people[0]!)).toEqual([])
    expect(storage).not.toHaveBeenCalled(); expect(network).not.toHaveBeenCalled()
  })
  it('人员页面显示指定七列，搜索空状态不渲染旧列表', async () => {
    const wrapper = mount(PeopleInformation, { global: { stubs } }); wrappers.push(wrapper)
    expect(wrapper.findAll('th').map(item => item.text())).toEqual(['ID', '人员名称', '部门', '岗位', '手机号', '角色', '操作'])
    await wrapper.get('input[aria-label="人员名称筛选"]').setValue('无此人员')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('暂无符合条件的人员')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  })
  it('刷新等同新页面会话，合成数据独立恢复', () => {
    const first = usePeopleAccessDemoStore()
    first.saveMapping('r1', [])
    setActivePinia(createPinia())
    const fresh = usePeopleAccessDemoStore()
    expect(fresh.data.positions[0]!.roleIds).toEqual(['r1'])
  })
})

describe('复刻与真实权限隔离', () => {
  it('匿名访问管理路由仍要求登录', async () => {
    const route = { meta: { requiresAuth: true }, fullPath: '/hbos/admin/people' }
    expect(await checkPortalAccess(route, { ensureSession: async () => false, bootstrapError: null, apps: [] }, 'frappe'))
      .toEqual({ path: '/hbos/login', query: { redirect_to: route.fullPath } })
  })
  it('演示页面只在 Mock 模式渲染，真实模式不渲染展示数据', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
    await router.push('/hbos/admin/people')
    const mockWrapper = mount(PeopleAccessDemoView, { global: { plugins: [router], stubs } }); wrappers.push(mockWrapper)
    expect(mockWrapper.find('.iam-page').exists()).toBe(true)
    mode.value = 'frappe'
    const realWrapper = mount(PeopleAccessDemoView, { global: { plugins: [router], stubs } }); wrappers.push(realWrapper)
    expect(realWrapper.find('.iam-page').exists()).toBe(false)
  })
  it('真实模式不能实例化展示数据', () => {
    mode.value = 'frappe'
    expect(() => usePeopleAccessDemoStore()).toThrow('仅供 Mock')
  })
  it.each(['frappe', 'mock'])('桌面与手机均展示管理入口，真实页面另用只读数据（%s）', async source => {
    mode.value = source
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
    await router.push('/hbos/admin/roles')
    for (const component of [PortalSidebar, MobilePortalNav]) {
      const wrapper = mount(component, { props: { workCount: 0 }, global: { plugins: [router] } }); wrappers.push(wrapper)
      const link = wrapper.find('a[href="/hbos/admin/people"]')
      expect(link.exists()).toBe(true)
      if (source === 'mock') expect(link.classes()).toContain('router-link-exact-active')
    }
  })
})
