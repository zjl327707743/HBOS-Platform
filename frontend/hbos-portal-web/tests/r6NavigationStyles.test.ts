import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(resolve(process.cwd(), 'src/theme/r6-experience.css'), 'utf8')

describe('R6 navigation link fidelity', () => {
  it('removes browser-default underlines from navigation links and link buttons', () => {
    expect(styles).toMatch(/\.r6-experience \.r6-global-nav a\s*,\s*\.r6-experience \.r6-local-nav a\s*,\s*\.r6-experience \.r6-mobile-local a\s*,\s*\.r6-experience \.r6-more-tools a\s*,\s*\.r6-experience a\.ant-btn\s*\{[^}]*text-decoration:\s*none/s)
  })
})
