<template>
  <canvas ref="canvasRef" class="pointer-fx-canvas"></canvas>
  <div class="pointer-aurora-vue" :style="{ transform: `translate3d(${x - 240}px, ${y - 240}px, 0)` }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const x = ref(typeof window !== 'undefined' ? window.innerWidth * 0.5 : 0)
const y = ref(typeof window !== 'undefined' ? window.innerHeight * 0.28 : 0)

let tx = x.value
let ty = y.value
let raf = 0
let renderRaf = 0
let lastSpawn = 0
let resizeHandler: (() => void) | null = null
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

function animatePointer() {
  x.value += (tx - x.value) * 0.17
  y.value += (ty - y.value) * 0.17
  raf = requestAnimationFrame(animatePointer)
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
  if (particles.length > 85) particles.splice(0, particles.length - 85)
}

function setupCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)

  const resize = () => {
    canvas.width = window.innerWidth * dpr
    canvas.height = window.innerHeight * dpr
    canvas.style.width = `${window.innerWidth}px`
    canvas.style.height = `${window.innerHeight}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }
  resizeHandler = resize
  window.addEventListener('resize', resize)
  resize()

  const render = () => {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)
    for (let i = particles.length - 1; i >= 0; i -= 1) {
      const p = particles[i]
      if (!p) continue
      p.x += p.vx
      p.y += p.vy
      p.life -= 0.018
      p.r *= 0.996
      if (p.life <= 0) {
        particles.splice(i, 1)
        continue
      }
      const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r)
      gradient.addColorStop(0, `rgba(${p.color},${0.07 * p.life})`)
      gradient.addColorStop(1, `rgba(${p.color},0)`)
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fill()
    }
    renderRaf = requestAnimationFrame(render)
  }
  render()
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  pointerHandler = (event: PointerEvent) => {
    tx = event.clientX
    ty = event.clientY
    const now = performance.now()
    if (now - lastSpawn > 35) {
      spawnParticle(event.clientX, event.clientY, Math.hypot(event.movementX || 0, event.movementY || 0))
      lastSpawn = now
    }
  }
  window.addEventListener('pointermove', pointerHandler, { passive: true })
  animatePointer()
  setupCanvas()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  cancelAnimationFrame(renderRaf)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (pointerHandler) window.removeEventListener('pointermove', pointerHandler)
})
</script>
