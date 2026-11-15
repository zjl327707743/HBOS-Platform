/** Browser-side structural assertions. Invoke against a settled knowledge route. */
export function probe() {
  const require = (condition, message) => { if (!condition) throw new Error(message) }
  const first = selector => {
    const el = document.querySelector(selector)
    require(el, 'Missing ' + selector)
    return el
  }
  const rect = el => el.getBoundingClientRect()
  const computed = el => getComputedStyle(el)
  require(document.styleSheets.length > 0, 'Missing stylesheets')
  const sidebar = first('.kb-sidebar-bottom')
  require(computed(sidebar).display === 'grid', 'V01 auxiliary navigation must be a grid')
  const links = [...sidebar.querySelectorAll('a')]
  require(links.length === 3, 'V01 expected all three auxiliary links')
  const rows = links.map(link => {
    const label = link.querySelector(':scope > span:last-child')
    require(label, 'V01 missing text label')
    const r = rect(link)
    const range = document.createRange()
    range.selectNodeContents(label)
    require(r.width > 110 && r.height > 0 && range.getClientRects().length === 1, 'V01 clipped or wrapped ' + label.textContent)
    require(computed(label).writingMode === 'horizontal-tb', 'V01 vertical writing mode')
    return { label: label.textContent, width: r.width, top: r.top }
  })
  require(new Set(rows.map(row => row.top)).size === rows.length, 'V01 links share a row')
  const results = { rows }
  if (location.pathname.endsWith('/maintenance/feedback')) {
    const heading = first('.maintenance-page .kb-heading')
    require(heading.querySelector('h1')?.textContent === '员工反馈', 'V03 wrong page title')
    require(heading.querySelector('p')?.textContent === '集中核对资料问题，让反馈有清楚的处理结果。', 'V03 wrong description')
    require(!heading.querySelector('button'), 'V03 unrelated heading action')
    const panel = first('.kb-staff-feedback')
    const feedbackSearch = panel.querySelector('input[aria-label="搜索员工反馈"]')
    require(feedbackSearch && !feedbackSearch.disabled, 'V04 supported feedback search must be enabled')
    require(panel.querySelectorAll('[data-v17-feedback-search-limitation]').length === 0, 'V04 must not show the fallback limitation when the candidate supports bounded search')
    const items = [...panel.querySelectorAll('.kb-staff-feedback-item')]
    require(items.length > 0, 'V02 zero feedback rows in populated scenario')
    const columns = first('.kb-staff-feedback-columns')
    results.feedback = items.map(item => {
      const icon = rect(item.querySelector('.kb-staff-icon'))
      const copy = rect(item.querySelector('.kb-staff-copy'))
      const expected = Number.parseFloat(computed(item).columnGap)
      require(Math.abs(copy.x - icon.right - expected) <= 2, 'V02 feedback content off track')
      if (rect(columns).width > 0) {
        for (const name of ['copy','status','action']) {
          const selector = '.kb-staff-' + name
          require(Math.abs(rect(columns.querySelector(selector)).left - rect(item.querySelector(selector)).left) <= 2 || name === 'action',
            'V02 header misalignment ' + name)
          if (name === 'action') require(Math.abs(rect(columns.querySelector(selector)).right - rect(item.querySelector(selector)).right) <= 2,
            'V02 action right edge misaligned')
        }
      }
      return { tracks: computed(item).gridTemplateColumns, gap: copy.x - icon.right, width: copy.width }
    })
  }
  return results
}
