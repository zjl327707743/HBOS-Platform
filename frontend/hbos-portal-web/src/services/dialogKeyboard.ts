/** Keep keyboard traversal inside the active drawer; nested portals own their events. */
export function cycleDialogTab(event: KeyboardEvent, root: HTMLElement) {
  if (event.key !== 'Tab' || event.defaultPrevented) return
  const nodes = Array.from(root.querySelectorAll<HTMLElement>(
    'a[href],button,input,select,textarea,[tabindex]',
  )).filter(node => node.tabIndex >= 0 && !node.matches(':disabled,input[type="hidden"]')
    && !node.closest('[inert]') && Array.from(node.getClientRects()).some(rect => rect.width > 0 && rect.height > 0)
    && getComputedStyle(node).visibility !== 'hidden')
  const first = nodes[0], last = nodes[nodes.length - 1]
  if (!first || !last) return
  const active = root.ownerDocument.activeElement
  if (!nodes.includes(active as HTMLElement) || (event.shiftKey ? active === first : active === last)) {
    event.preventDefault()
    ;(event.shiftKey ? last : first).focus()
  }
}
