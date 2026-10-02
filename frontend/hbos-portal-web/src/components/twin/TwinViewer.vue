<template>
  <section class="twin-viewport" aria-label="M607B 受保护三维模型查看器">
    <canvas
      ref="canvas"
      tabindex="0"
      aria-label="M607B 三维模型。拖动转动，滚轮缩放；点击部件以选择。"
      @keydown="onKeydown"
    ></canvas>

    <div class="viewer-top">
      <div>
        <a-tag color="purple">真实获批模型</a-tag>
        <span>{{ manifest.label }} · {{ manifest.site_identity }}</span>
      </div>
      <a-tag>{{ manifest.connection_state === 'not_connected' ? '未接现场' : manifest.connection_state }}</a-tag>
    </div>

    <div class="viewer-tools" aria-label="查看器工具">
      <a-tooltip title="聚焦已选部件"><button type="button" :disabled="!selectedAssetId" @click="focusSelected"><AimOutlined /></button></a-tooltip>
      <a-tooltip :title="isolated ? '退出隔离' : '隔离已选部件'"><button type="button" :class="{ active: isolated }" :disabled="!selectedAssetId" @click="toggleIsolate"><PartitionOutlined /></button></a-tooltip>
      <a-tooltip title="切换线框"><button type="button" :class="{ active: wireframe }" @click="toggleWireframe"><BorderOutlined /></button></a-tooltip>
      <a-tooltip title="复位视图"><button type="button" @click="resetView"><ReloadOutlined /></button></a-tooltip>
    </div>

    <div v-if="loading" class="viewer-state">
      <a-spin size="large" />
      <strong>正在校验并载入真实模型</strong>
      <span>{{ progress }}%</span>
    </div>
    <div v-else-if="error" class="viewer-state error">
      <WarningOutlined />
      <strong>模型暂时无法显示</strong>
      <span>{{ error }}</span>
      <a-button @click="loadModel">重试</a-button>
    </div>

    <div v-if="isolated && selectedAssetId" class="isolate-chip">隔离查看 · {{ selectedAssetId }}</div>
    <div class="viewer-bottom">
      <span><span class="mouse-mark">◎</span> 拖动转动 · 滚轮缩放 · 点击选择</span>
      <span>{{ manifest.fit_disclaimer }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  AimOutlined,
  BorderOutlined,
  PartitionOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { TwinManifest } from '@/contracts/p1'

const props = defineProps<{ manifest: TwinManifest }>()
const emit = defineEmits<{
  (event: 'select', assetId: string | null): void
  (event: 'ready'): void
  (event: 'error', message: string): void
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const loading = ref(true)
const progress = ref(0)
const error = ref<string | null>(null)
const selectedAssetId = ref<string | null>(null)
const isolated = ref(false)
const wireframe = ref(false)

let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let modelRoot: THREE.Object3D | null = null
let selectedNode: THREE.Object3D | null = null
let resizeObserver: ResizeObserver | null = null
let disposed = false
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()
const originalView = {
  position: new THREE.Vector3(),
  target: new THREE.Vector3(),
}
const highlighted = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>()

function render() {
  if (!renderer || !scene || !camera || disposed) return
  renderer.render(scene, camera)
}

function frameObject(object: THREE.Object3D, padding = 1.35) {
  if (!camera || !controls) return
  const box = new THREE.Box3().setFromObject(object)
  if (box.isEmpty()) return
  const sphere = box.getBoundingSphere(new THREE.Sphere())
  const radius = Math.max(sphere.radius, 0.01)
  const halfFov = THREE.MathUtils.degToRad(camera.fov / 2)
  const distance = (radius / Math.tan(halfFov)) * padding
  const direction = new THREE.Vector3(1, 0.72, 1).normalize()
  camera.position.copy(sphere.center).addScaledVector(direction, distance)
  camera.near = Math.max(distance / 1000, 0.001)
  camera.far = Math.max(distance * 50, 100)
  camera.updateProjectionMatrix()
  controls.target.copy(sphere.center)
  controls.update()
  render()
}

function cloneHighlight(material: THREE.Material): THREE.Material {
  const clone = material.clone()
  const standard = clone as THREE.MeshStandardMaterial
  if (standard.emissive?.isColor) {
    standard.emissive.set('#5c63ff')
    standard.emissiveIntensity = 0.7
  } else if (standard.color?.isColor) {
    standard.color.lerp(new THREE.Color('#7069ff'), 0.48)
  }
  return clone
}

function clearHighlight() {
  for (const [mesh, original] of highlighted) {
    const active = mesh.material
    const activeMaterials = Array.isArray(active) ? active : [active]
    activeMaterials.forEach((material) => material.dispose())
    mesh.material = original
  }
  highlighted.clear()
}

function applyHighlight(node: THREE.Object3D) {
  clearHighlight()
  node.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    highlighted.set(child, child.material)
    child.material = Array.isArray(child.material)
      ? child.material.map(cloneHighlight)
      : cloneHighlight(child.material)
  })
}

function assetNodeFor(object: THREE.Object3D | null): THREE.Object3D | null {
  let current = object
  while (current && current !== modelRoot?.parent) {
    if (typeof current.userData?.asset_id === 'string' && current.userData.asset_id.trim()) {
      return current
    }
    current = current.parent
  }
  return null
}

function selectNode(node: THREE.Object3D | null) {
  if (isolated.value) restoreVisibility()
  selectedNode = node
  selectedAssetId.value = node ? String(node.userData.asset_id) : null
  if (node) applyHighlight(node)
  else clearHighlight()
  emit('select', selectedAssetId.value)
  render()
}

function pick(event: PointerEvent) {
  if (!canvas.value || !camera || !modelRoot || loading.value || error.value) return
  const rect = canvas.value.getBoundingClientRect()
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const intersections = raycaster.intersectObject(modelRoot, true)
  const node = intersections.length ? assetNodeFor(intersections[0]?.object || null) : null
  selectNode(node)
}

function restoreVisibility() {
  modelRoot?.traverse((node) => { node.visible = true })
  isolated.value = false
}

function toggleIsolate() {
  if (!modelRoot || !selectedNode) return
  if (isolated.value) {
    restoreVisibility()
  } else {
    const selectedObjects = new Set<THREE.Object3D>()
    selectedNode.traverse((item) => selectedObjects.add(item))
    modelRoot.traverse((item) => {
      if (item instanceof THREE.Mesh) item.visible = selectedObjects.has(item)
    })
    isolated.value = true
  }
  render()
}

function focusSelected() {
  if (selectedNode) frameObject(selectedNode, 1.7)
}

function toggleWireframe() {
  wireframe.value = !wireframe.value
  modelRoot?.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return
    const materials = Array.isArray(node.material) ? node.material : [node.material]
    materials.forEach((material) => {
      const candidate = material as THREE.MeshStandardMaterial
      if ('wireframe' in candidate) candidate.wireframe = wireframe.value
    })
  })
  render()
}

function resetView() {
  if (!camera || !controls) return
  restoreVisibility()
  camera.position.copy(originalView.position)
  controls.target.copy(originalView.target)
  controls.update()
  render()
}

function onKeydown(event: KeyboardEvent) {
  if (!camera || !controls) return
  if (event.key.toLowerCase() === 'r') resetView()
  if (event.key === '+' || event.key === '=') {
    camera.position.lerp(controls.target, 0.12)
    controls.update(); render()
  }
  if (event.key === '-') {
    camera.position.sub(controls.target).multiplyScalar(1.12).add(controls.target)
    controls.update(); render()
  }
}

function disposeObjectResources(object: THREE.Object3D) {
  object.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return
    node.geometry.dispose()
    const materials = Array.isArray(node.material) ? node.material : [node.material]
    materials.forEach((material) => {
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) value.dispose()
      }
      material.dispose()
    })
  })
}

function disposeScene() {
  disposed = true
  clearHighlight()
  restoreVisibility()
  canvas.value?.removeEventListener('pointerup', pick)
  controls?.removeEventListener('change', render)
  controls?.dispose()
  resizeObserver?.disconnect()
  if (modelRoot) disposeObjectResources(modelRoot)
  renderer?.dispose()
  renderer?.forceContextLoss()
  renderer = null
  scene = null
  camera = null
  controls = null
  modelRoot = null
  selectedNode = null
}

function resize() {
  if (!canvas.value || !renderer || !camera) return
  const width = Math.max(1, canvas.value.clientWidth)
  const height = Math.max(1, canvas.value.clientHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  render()
}

function initializeRenderer() {
  if (!canvas.value) return
  disposed = false
  renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.12
  scene = new THREE.Scene()
  scene.background = new THREE.Color('#eef4fb')
  scene.environment = null
  camera = new THREE.PerspectiveCamera(38, 1, 0.01, 10000)
  controls = new OrbitControls(camera, canvas.value)
  controls.enableDamping = false
  controls.screenSpacePanning = true
  controls.addEventListener('change', render)
  scene.add(new THREE.HemisphereLight('#dbe9ff', '#7b8796', 2.2))
  const key = new THREE.DirectionalLight('#ffffff', 3.1)
  key.position.set(6, 10, 8)
  scene.add(key)
  const fill = new THREE.DirectionalLight('#8da7ff', 1.8)
  fill.position.set(-8, 3, -5)
  scene.add(fill)
  canvas.value.addEventListener('pointerup', pick)
  canvas.value.addEventListener('webglcontextlost', (event) => {
    event.preventDefault()
    error.value = '浏览器图形上下文已丢失，请刷新或重试。'
    emit('error', error.value)
  }, { once: true })
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(canvas.value)
  resize()
}

function loadModel() {
  if (!scene) return
  loading.value = true
  progress.value = 0
  error.value = null
  const loader = new GLTFLoader()
  loader.setWithCredentials(true)
  loader.load(
    props.manifest.model_url,
    (gltf) => {
      if (disposed || !scene) {
        disposeObjectResources(gltf.scene)
        return
      }
      modelRoot = gltf.scene
      scene.add(modelRoot)
      frameObject(modelRoot)
      if (camera && controls) {
        originalView.position.copy(camera.position)
        originalView.target.copy(controls.target)
      }
      loading.value = false
      progress.value = 100
      emit('ready')
      render()
    },
    (event) => {
      if (event.total > 0) progress.value = Math.min(99, Math.round((event.loaded / event.total) * 100))
    },
    () => {
      loading.value = false
      error.value = '模型加载或完整性校验失败；没有使用替代几何。'
      emit('error', error.value)
    },
  )
}

onMounted(() => {
  initializeRenderer()
  loadModel()
})
onBeforeUnmount(disposeScene)

defineExpose({ focusSelected, resetView, toggleIsolate })
</script>

<style scoped>
.twin-viewport { position:relative;overflow:hidden;min-height:650px;border:1px solid rgba(255,255,255,.82);border-radius:26px;background:radial-gradient(circle at 70% 30%,rgba(92,110,255,.12),transparent 29%),linear-gradient(180deg,#f5f9fe,#eaf2fa);box-shadow:var(--hbos-shadow-card); }
canvas { display:block;width:100%;height:650px;outline:none;cursor:grab; }
canvas:active { cursor:grabbing; }
.viewer-top { position:absolute;z-index:2;top:17px;left:17px;right:17px;display:flex;justify-content:space-between;gap:12px;pointer-events:none; }
.viewer-top > div { display:flex;align-items:center;gap:9px; }
.viewer-top span { color:#576b8b;font-size:10px;font-weight:700; }
.viewer-tools { position:absolute;z-index:3;top:68px;right:17px;display:grid;gap:7px; }
.viewer-tools button { display:grid;width:38px;height:38px;place-items:center;border:1px solid rgba(65,91,138,.12);border-radius:12px;background:rgba(255,255,255,.82);color:#526786;box-shadow:0 8px 22px rgba(47,72,117,.08);cursor:pointer;backdrop-filter:blur(12px); }
.viewer-tools button.active { color:#fff;background:#6268f4; }.viewer-tools button:disabled{opacity:.42;cursor:not-allowed}
.viewer-state { position:absolute;z-index:4;inset:0;display:grid;place-content:center;justify-items:center;gap:11px;background:rgba(239,246,252,.82);color:#365071;backdrop-filter:blur(10px); }
.viewer-state strong { font-size:14px; }.viewer-state span { max-width:340px;text-align:center;color:#76869e;font-size:11px;line-height:1.6; }
.viewer-state.error > :first-child { color:#d9784c;font-size:30px; }
.isolate-chip { position:absolute;left:17px;bottom:60px;padding:7px 10px;border-radius:10px;background:rgba(33,50,81,.78);color:#fff;font-size:10px;backdrop-filter:blur(12px); }
.viewer-bottom { position:absolute;z-index:2;left:17px;right:17px;bottom:15px;display:flex;justify-content:space-between;gap:12px;color:#697c98;font-size:10px;pointer-events:none; }
.mouse-mark { color:#6268f4;font-size:13px; }
@media (max-width: 700px) { .twin-viewport{min-height:500px}canvas{height:500px}.viewer-top>div span{display:none}.viewer-bottom{flex-direction:column}.viewer-bottom span:last-child{display:none} }
</style>
