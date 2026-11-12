import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

/**
 * 同源 iframe 内嵌 Desk 页面时，剥掉 Desk 的外壳导航。
 *
 * 为什么需要：11 个后台面（4 张报表、4 个列表、3 个操作页）按
 * docs/frontend/FRONTEND_IMPLEMENTATION_GUIDE.md §1.2 不重写成原生前端，
 * 而是同域 iframe 内嵌。直接嵌入会把 Desk 的顶栏与左侧栏一起带进来，
 * 门户侧栏之外再套一层导航，观感与可用性都差。
 *
 * 为什么能这样做：门户与 Frappe 同源（dev 由 Vite 代理收敛到 5178，生产由
 * portal 容器收敛到单一来源），故 iframe 的 contentDocument 可访问。
 *
 * **失败即降级**：取不到文档、或选择器一个都没命中，就什么都不做——
 * 最坏退化成「带 Desk 外壳」的原样嵌套，功能不受影响，绝不抛错阻断渲染。
 */

// 要隐藏的 Desk 外壳。集中在顶部便于 Frappe 升级后一处修改。
// 这些类名已实测存在于生产 desk.bundle.css。
const CHROME_SELECTORS = [
  '.navbar',
  '.body-sidebar',
  '.body-sidebar-container',
  '.body-sidebar-placeholder',
  '.body-sidebar-top',
  '.body-sidebar-bottom',
  '.standard-sidebar',
  '.layout-side-section',
]

// 去掉宽度约束，否则隐藏侧栏后右侧会留一大块空白。
const WIDEN_SELECTORS = [
  '.layout-main',
  '.layout-main-section-wrapper',
  '.layout-main-section',
  '.page-container',
  '.container',
]

// 共享视觉层（hbos_attendance.bundle.css）由 hooks.py 的 app_include_css 全局注入，
// 但它的每条规则都限定在 `.hbos-surface` 下——而 6 个自定义 Desk 页是自己挂这个
// class 的，**报表与列表页不挂**。结果：同域内嵌报表时，令牌、字体、画布全不生效，
// 报表是原始 Frappe 观感，与门户其余部分割裂。
//
// 这里替它们补上挂载点。选 `.content.page-container`（报表页实测的承载容器），
// 退而求其次用 body。
const SURFACE_TARGETS = ['.content.page-container', '.page-container', '.main-section']

// 只给「自己没有挂」的页面补：自定义页已挂 `.hbos-surface`，再套一层会导致
// 双重内边距与双重极光层。
const SURFACE_CLASS = 'hbos-surface'

const STYLE_ID = 'hbos-embed-shell-strip'

function buildCss() {
  return `
${CHROME_SELECTORS.join(',\n')} { display: none !important; }

/* 外壳去掉后，页头保留（它承载报表的查询条件与操作按钮，删掉会让页面不可用），
   只把它的背景与分隔线抹平，使其融进画布。 */
.page-head { background: transparent !important; border-bottom: none !important; }

${WIDEN_SELECTORS.join(',\n')} { max-width: none !important; }

/* 侧栏原本占位导致的左内边距归零 */
.page-container > .page-body,
.layout-main-section-wrapper { padding-left: 0 !important; }

/* 内嵌页面自己再叠一层滚动条会与门户滚动打架，交由 iframe 自身滚动 */
html, body { overflow-x: hidden; }
`
}

function mountSurface(doc: Document): boolean {
  // 页面自己挂了就不补（自定义页属于这种），否则会叠出双重内边距与双层极光
  if (doc.querySelector('.' + SURFACE_CLASS)) return true

  for (const selector of SURFACE_TARGETS) {
    const target = doc.querySelector(selector)
    if (target) {
      target.classList.add(SURFACE_CLASS)
      // 数据密集页（报表 / 列表）不铺极光：内容密度高，背景装饰只会干扰读数。
      // 对应 bundle 里的 .hbos-surface--data。
      target.classList.add('hbos-surface--data')
      return true
    }
  }
  // 一个目标都没命中 → 不硬塞到 body 上（body 加 padding 会打乱 Frappe 布局），
  // 如实返回 false，页面退化为原始观感但依然可用。
  return false
}

function injectInto(doc: Document, win: Window & typeof globalThis) {
  if (!doc.getElementById(STYLE_ID)) {
    const style = doc.createElement('style')
    style.id = STYLE_ID
    style.textContent = buildCss()
    doc.head.appendChild(style)
  }
  win.document.documentElement?.classList.add('hbos-embedded')
}

export function useDeskEmbed(frameRef: Ref<HTMLIFrameElement | null>) {
  const stripped = ref(false)

  function apply() {
    const frame = frameRef.value
    if (!frame) return
    let doc: Document | null = null
    try {
      doc = frame.contentDocument
    } catch {
      // 跨源（理论上不会发生，同源前提由代理与容器保证）→ 静默降级
      return
    }
    if (!doc || !doc.head) return

    // 是否真的命中了外壳：一个都没命中就不算剥离成功，
    // 但仍注入样式（无害），只是如实上报状态。
    const hit = CHROME_SELECTORS.some((sel) => doc!.querySelector(sel))
    try {
      injectInto(doc, frame.contentWindow as Window & typeof globalThis)
      const surfaced = mountSurface(doc)
      // 两件事都做到才算「已融入门户」：去掉 Desk 外壳 + 接上共享视觉层
      stripped.value = hit && surfaced
    } catch {
      return
    }
  }

  function onLoad() {
    // 交给浏览器完成布局后再操作文档，避免读到尚未构建完的 head
    window.requestAnimationFrame(() => {
      apply()
      // Desk 是 SPA，外壳在首帧之后可能才挂载；补一次延迟重试。
      window.setTimeout(apply, 300)
    })
  }

  watch(frameRef, (frame) => {
    if (!frame) {
      stripped.value = false
      return
    }
    frame.addEventListener('load', onLoad)
    // 已在缓存中、注册监听时 load 已过的情况：立即尝试一次
    onLoad()
  })

  onBeforeUnmount(() => {
    frameRef.value?.removeEventListener('load', onLoad)
  })

  return { stripped, apply }
}
