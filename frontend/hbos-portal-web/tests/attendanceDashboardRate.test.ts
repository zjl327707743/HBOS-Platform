import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'

const api = vi.hoisted(() => ({ fetch: vi.fn() }))
vi.mock('@/services/attendance', async (importOriginal) => ({ ...(await importOriginal<object>()), fetchAttendanceDashboard: api.fetch }))

import AttendanceDashboardView from '@/views/AttendanceDashboardView.vue'

const base = {
  scope: null, coverage: null, total_late: 0, total_early: 0, total_absent: 0, anomaly_people: 0,
  total_employees: 4, daily_avg_late: 0, date_range: '2026-10-16 ~ 2026-10-22',
  top_late_names: [], top_late_counts: [], top_absent_names: [], top_absent_counts: [],
  dept_names: [], dept_late: [], dept_early: [], dept_absent: [],
  trend_labels: [], trend_late: [], trend_early: [],
}

function mountView () {
  return mount(AttendanceDashboardView, { global: { plugins: [Antd], stubs: { 'a-skeleton': true, 'a-empty': true } } })
}

beforeEach(() => vi.resetAllMocks())

it('renders a neutral placeholder instead of `null%` when the rate is not measurable', async () => {
  api.fetch.mockResolvedValue({ ...base, attendance_rate: null })
  const wrapper = mountView()
  await flushPromises()
  const text = wrapper.text()
  expect(text).not.toContain('null%')
  expect(text).toContain('出勤率')
  expect(text).toContain('—')
  expect(text).toContain('当前区间暂无数据')
  wrapper.unmount()
})

it('keeps a real 0% distinguishable from an unmeasurable rate', async () => {
  api.fetch.mockResolvedValue({ ...base, attendance_rate: 0 })
  const wrapper = mountView()
  await flushPromises()
  expect(wrapper.text()).toContain('0%')
  expect(wrapper.text()).not.toContain('当前区间暂无数据')
  wrapper.unmount()
})

it('treats an out-of-range backend rate as not measurable instead of a healthy figure', async () => {
  for (const value of [-16.7, 101]) {
    api.fetch.mockResolvedValue({ ...base, attendance_rate: value })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).not.toContain(`${value}%`)
    expect(wrapper.text()).toContain('—')
    wrapper.unmount()
  }
})
