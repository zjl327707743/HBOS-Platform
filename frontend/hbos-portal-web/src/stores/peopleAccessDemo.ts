import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { portalDataSource } from '@/services/portalProvider'
import { createPeopleAccessDemoData } from '@/data/mockPeopleAccess'
import type { DemoPerson, DemoPersonFilter, DemoRole } from '@/contracts/peopleAccessDemo'

export const usePeopleAccessDemoStore = defineStore('people-access-demo', () => {
  if (portalDataSource !== 'mock') throw new Error('人员与权限复刻数据仅供 Mock 模式使用。')
  const data = reactive(createPeopleAccessDemoData())
  const departmentName = (id: string) => data.departments.find(item => item.id === id)?.name || ''
  const personPositions = (person: Pick<DemoPerson, 'positionIds'>) =>
    person.positionIds.flatMap(id => data.positions.filter(item => item.id === id))
  const personRoles = (person: Pick<DemoPerson, 'positionIds'>) => {
    const ids = new Set(personPositions(person).flatMap(item => item.roleIds))
    return data.roles.filter(item => ids.has(item.id))
  }
  function inDepartment(id: string, root: string, includeChildren: boolean) {
    const visited = new Set<string>()
    let current: string | null = id
    while (current && !visited.has(current)) {
      if (current === root) return true
      if (!includeChildren) return false
      visited.add(current)
      current = data.departments.find(item => item.id === current)?.parentId || null
    }
    return false
  }
  function filterPeople(filter: DemoPersonFilter) {
    return data.people.filter(person => person.name.includes(filter.name) && person.phone.includes(filter.phone)
      && (!filter.roleId || personRoles(person).some(role => role.id === filter.roleId))
      && (!filter.position || personPositions(person).some(position => position.name === filter.position))
      && personPositions(person).some(position => inDepartment(position.departmentId, filter.departmentId, filter.includeChildren)))
  }
  const departmentCount = (id: string) => data.people.filter(person =>
    personPositions(person).some(position => inDepartment(position.departmentId, id, true))).length
  const positionCount = (id: string) => data.people.filter(person => person.positionIds.includes(id)).length
  const nextPersonId = () => `HB${String(Math.max(0, ...data.people.map(person => Number(person.id.slice(2)))) + 1).padStart(3, '0')}`
  function validatePerson(value: DemoPerson) {
    const name = value.name.trim(), phone = value.phone.trim()
    if (!name || name.length > 30 || !/^1[0-9*]{10}$/.test(phone)) throw new Error('请填写人员名称和 11 位手机号或演示脱敏号码。')
    if (!value.positionIds.length || value.positionIds.some(id => !data.positions.some(position => position.id === id))) throw new Error('请选择完整的部门与岗位。')
    if (new Set(value.positionIds).size !== value.positionIds.length) throw new Error('同一人员不能重复选择同一个岗位。')
    return { name, phone }
  }
  function savePerson(value: DemoPerson, existingId?: string) {
    const { name, phone } = validatePerson(value)
    const existing = data.people.find(person => person.id === existingId)
    if (existingId && !existing) throw new Error('人员记录已不存在，请重新打开。')
    const saved = { ...value, id: existing?.id || nextPersonId(), name, phone, positionIds: [...value.positionIds] }
    if (existing) Object.assign(existing, saved)
    else data.people.push(saved)
  }
  function saveRole(value: Pick<DemoRole, 'name' | 'description' | 'permissionIds'>, existingId?: string) {
    const name = value.name.trim()
    if (!name || name.length > 30) throw new Error('请输入 1—30 字的角色名称。')
    if (data.roles.some(role => role.name === name && role.id !== existingId)) throw new Error('角色名称已存在，请使用其他名称。')
    const known = new Set(data.directory.flatMap(app => app.menus.flatMap(menu => menu.actions.map(action => action.id))))
    if (value.permissionIds.some(id => !known.has(id))) throw new Error('所选功能已不在当前目录，请重新选择。')
    const existing = data.roles.find(role => role.id === existingId)
    if (existingId && !existing) throw new Error('角色已不存在，请重新打开。')
    const saved = { name, description: value.description.trim().slice(0, 200), permissionIds: [...new Set(value.permissionIds)] }
    if (existing) Object.assign(existing, saved)
    else data.roles.push({ ...saved, id: `r${Math.max(0, ...data.roles.map(role => Number(role.id.slice(1)))) + 1}`, createdAt: new Date().toLocaleDateString('sv-SE') })
  }
  function mappingChanges(roleId: string, selected: string[]) {
    const changed = data.positions.filter(position => position.roleIds.includes(roleId) !== selected.includes(position.id))
    const affected = data.people.filter(person => person.positionIds.some(id => changed.some(position => position.id === id)))
    return { changed, affected }
  }
  function saveMapping(roleId: string, selected: string[]) {
    if (!data.roles.some(role => role.id === roleId) || selected.some(id => !data.positions.some(position => position.id === id))) throw new Error('角色或岗位已不存在，请重新打开。')
    for (const position of data.positions) {
      position.roleIds = position.roleIds.filter(id => id !== roleId)
      if (selected.includes(position.id)) position.roleIds.push(roleId)
    }
  }
  function deleteRole(id: string) {
    if (data.positions.some(position => position.roleIds.includes(id))) throw new Error('该角色已关联岗位，请先解除岗位关联后再删除。')
    data.roles = data.roles.filter(role => role.id !== id)
  }
  return { data, departmentName, personPositions, personRoles, filterPeople, departmentCount, positionCount,
    nextPersonId, validatePerson, savePerson, saveRole, mappingChanges, saveMapping, deleteRole }
})
