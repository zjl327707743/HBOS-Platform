import assert from 'node:assert/strict'
import test from 'node:test'
import { getRoleLabel } from '../src/features/auth/roleLabel.ts'

test('maps actual backend LIMS roles', () => {
  assert.equal(getRoleLabel(['LIMS Manager'], true), 'LIMS 经理')
  assert.equal(getRoleLabel(['LIMS Reviewer'], true), 'LIMS 复核人')
  assert.equal(getRoleLabel(['LIMS Analyst'], true), 'LIMS 检验员')
  assert.equal(getRoleLabel(['LIMS QA'], true), 'QA')
  assert.equal(getRoleLabel(['LIMS QA Manager'], true), 'QA 经理')
  assert.equal(getRoleLabel(['LIMS QP'], true), '质量受权人')
})

test('shows System Manager and authenticated fallback accurately', () => {
  assert.equal(getRoleLabel(['System Manager'], true), '系统管理员')
  assert.equal(getRoleLabel(['Employee'], true), '已登录')
  assert.equal(getRoleLabel([], false), '未登录')
})
