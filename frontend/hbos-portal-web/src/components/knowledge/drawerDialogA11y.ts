/**
 * Ant Design Vue Drawer does not forward role/aria-modal to its root DOM node and its
 * content exposes no dialog name. Each drawer instance gets its own unique root class so
 * overlapping drawers keep their own name and title association.
 *
 * Open order is tracked explicitly because the portal DOM position is fixed by the first
 * mount, not by which drawer opened last. The latest opened instance is the top layer:
 * only it is aria-modal, covered instances pause interaction (inert).
 */
const drawerOrder = new Map<string, number>()
const drawerRoots = new Map<string, HTMLElement>()
let order = 0

export function markDrawerDialogRoot(rootClassName: string, label: string, modal = false): boolean {
  const root = document.querySelector<HTMLElement>(`.ant-drawer.${rootClassName}`)
  if (!root) return false
  root.setAttribute('role', 'dialog')
  root.setAttribute('aria-label', label)
  if (modal) root.setAttribute('aria-modal', 'true')
  const title = root.querySelector<HTMLElement>('.ant-drawer-title')
  if (title) {
    const titleId = `${rootClassName}-title`
    title.id = titleId
    root.setAttribute('aria-labelledby', titleId)
  }
  if (root.classList.contains('ant-drawer-open')) {
    if (!drawerOrder.has(rootClassName)) drawerOrder.set(rootClassName, ++order)
    drawerRoots.set(rootClassName, root)
  }
  return true
}

/** Call when a drawer starts closing so a later drawer cannot inherit its layer. */
export function forgetDrawerDialogRoot(rootClassName: string): void {
  drawerOrder.delete(rootClassName)
  drawerRoots.delete(rootClassName)
  syncDrawerDialogStack()
}

/** Only the top-most open drawer is a modal dialog; covered instances pause interaction. */
export function syncDrawerDialogStack(): void {
  const open = [...drawerRoots.entries()]
    .filter(([, root]) => root.isConnected && root.classList.contains('ant-drawer-open'))
    .sort((a, b) => (drawerOrder.get(a[0]) ?? 0) - (drawerOrder.get(b[0]) ?? 0))
  open.forEach(([, root], index) => {
    const top = index === open.length - 1
    const wrapper = root.querySelector<HTMLElement>('.ant-drawer-content-wrapper')
    if (top) {
      root.setAttribute('aria-modal', 'true')
      wrapper?.removeAttribute('inert')
    } else {
      root.removeAttribute('aria-modal')
      wrapper?.setAttribute('inert', '')
    }
  })
}

/** Top-most currently open knowledge drawer (explicit open order, not DOM order). */
export function topDrawerDialogRoot(): HTMLElement | null {
  const open = [...drawerRoots.entries()]
    .filter(([, root]) => root.isConnected && root.classList.contains('ant-drawer-open'))
    .sort((a, b) => (drawerOrder.get(a[0]) ?? 0) - (drawerOrder.get(b[0]) ?? 0))
  const top = open[open.length - 1]
  return top ? top[1] : null
}

/** Shared after-open-change handler for the single-instance knowledge drawers. */
export function handleDrawerLayerChange(rootClassName: string, label: string, open: boolean): void {
  if (open) {
    const apply = () => { markDrawerDialogRoot(rootClassName, label); syncDrawerDialogStack() }
    apply()
    window.setTimeout(apply, 80)
    window.setTimeout(apply, 260)
    return
  }
  window.setTimeout(() => forgetDrawerDialogRoot(rootClassName), 0)
  window.setTimeout(() => syncDrawerDialogStack(), 120)
}
