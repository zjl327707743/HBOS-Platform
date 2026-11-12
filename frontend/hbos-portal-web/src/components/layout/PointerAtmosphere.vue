<template>
  <canvas ref="canvasRef" class="pointer-fx-canvas" aria-hidden="true"></canvas>
  <div class="pointer-aurora-vue" aria-hidden="true" :style="{ transform: `translate3d(${x - 240}px, ${y - 240}px, 0)` }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ paused?: boolean }>(), { paused: false })
const canvasRef = ref<HTMLCanvasElement | null>(null)
const x = ref(typeof window !== 'undefined' ? window.innerWidth * 0.5 : 0)
const y = ref(typeof window !== 'undefined' ? window.innerHeight * 0.28 : 0)

let tx = x.value
let ty = y.value
let raf = 0
let previousFrame = 0
let context: CanvasRenderingContext2D | null = null
let coarse: MediaQueryList | null = null
let lastSpawn = 0
let resizeHandler: (() => void) | null = null
let motion: MediaQueryList | null = null
let running = false
let pointerHandler: ((event: PointerEvent) => void) | null = null

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  life: number
  color: string
}

const particles: Particle[] = []

function wake() {
  if (!raf && running) {
    previousFrame = 0
    raf = requestAnimationFrame(render)
  }
}

function render(now: number) {
  raf = 0
  if (!running) return
  const dt = previousFrame ? Math.min((now - previousFrame) / 16.667, 3) : 1
  previousFrame = now
  const follow = 1 - Math.pow(.83, dt)
  x.value += (tx - x.value) * follow
  y.value += (ty - y.value) * follow
  const ctx = context
  if (ctx) {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
    for (let i = particles.length - 1; i >= 0; i -= 1) {
      const p = particles[i]
      if (!p) continue
      p.x += p.vx * dt
      p.y += p.vy * dt
      p.life -= .018 * dt
      if (p.life <= 0) { particles.splice(i, 1); continue }
      const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r)
      gradient.addColorStop(0, 'rgba(' + p.color + ',' + (.11 * p.life) + ')')
      gradient.addColorStop(1, 'rgba(' + p.color + ',0)')
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  if (particles.length || Math.hypot(tx - x.value, ty - y.value) > .3) raf = requestAnimationFrame(render)
}

function spawnParticle(px: number, py: number, speed: number) {
  const count = Math.min(3, 1 + Math.floor(speed / 18))
  const colors = ['103,95,255', '73,168,255', '72,214,189']
  for (let i = 0; i < count; i += 1) {
    particles.push({
      x: px + (Math.random() - 0.5) * 12,
      y: py + (Math.random() - 0.5) * 12,
      vx: (Math.random() - 0.5) * 0.35,
      vy: -0.08 - Math.random() * 0.25,
      r: 4 + Math.random() * 12,
      life: 1,
      color: colors[Math.floor(Math.random() * colors.length)] ?? '103,95,255',
    })
  }
  if (particles.length > 60) particles.splice(0, particles.length - 60)
}

function setupCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  context = ctx
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * dpr
    canvas.style.width = window.innerWidth + 'px'
    canvas.style.height = window.innerHeight + 'px'
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
  resizeHandler = resize
  window.addEventListener('resize', resize)
  resize()
}

function stop() {
  cancelAnimationFrame(raf)
  raf = 0
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (pointerHandler) window.removeEventListener('pointermove', pointerHandler)
  context?.clearRect(0, 0, window.innerWidth, window.innerHeight)
  context = null
  particles.length = 0
  running = false
}
function synchronizeMotion() {
  if (props.paused || document.visibilityState === 'hidden' || motion?.matches || coarse?.matches) { stop(); return }
  if (running) return
  running = true
  pointerHandler = (event: PointerEvent) => {
    if (event.pointerType === 'touch') return
    tx = event.clientX
    ty = event.clientY
    const now = performance.now()
    if (context && now - lastSpawn > 35) {
      spawnParticle(tx, ty, Math.hypot(event.movementX || 0, event.movementY || 0))
      lastSpawn = now
    }
    wake()
  }
  window.addEventListener('pointermove', pointerHandler, { passive: true })
  setupCanvas()
  wake()
}
watch(() => props.paused, synchronizeMotion)
onMounted(() => {
  motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  coarse = window.matchMedia('(pointer: coarse)')
  coarse.addEventListener('change', synchronizeMotion)
  motion.addEventListener('change', synchronizeMotion)
  document.addEventListener('visibilitychange', synchronizeMotion)
  synchronizeMotion()
})
onBeforeUnmount(() => {
  stop()
  motion?.removeEventListener('change', synchronizeMotion)
  coarse?.removeEventListener('change', synchronizeMotion)
  document.removeEventListener('visibilitychange', synchronizeMotion)
})
</script>
