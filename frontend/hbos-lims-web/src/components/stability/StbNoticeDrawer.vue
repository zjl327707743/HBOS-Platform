<template>
  <a-drawer v-model:open="open" title="新建稳定性考察通知" :width="560" placement="right">
    <p class="stb-gate-sub">原型入口 · 尚未连接业务服务</p>
    <div class="stb-drawer-section">
      <h3>基础信息</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>产品 *</label>
          <a-select v-model:value="form.product" :options="productOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>考察分类 *</label>
          <a-select v-model:value="form.category" :options="categoryOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>批次范围</label>
          <a-input v-model:value="form.batches" />
        </div>
        <div class="stb-form-field">
          <label>负责人</label>
          <a-input v-model:value="form.owner" />
        </div>
        <div class="stb-form-field full">
          <label>备注</label>
          <a-textarea v-model:value="form.remark" :rows="3" placeholder="填写申请依据、批次来源或补充说明" />
        </div>
      </div>
    </div>
    <div class="stb-notice">
      提交后进入通知单状态机；批准后方案字段将转为冻结快照，变更需要走版本化入口。
    </div>
    <template #footer>
      <a-button @click="open = false">取消</a-button>
      <a-button type="primary" @click="saveDraft">保存草稿</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { message } from 'ant-design-vue'

const open = ref(false)

const form = reactive({
  product: 'TEST 片剂 A',
  category: '新产品 / 工艺验证类',
  batches: 'T260901, T260902, T260903',
  owner: '林质检',
  remark: '',
})

const productOptions = ['TEST 片剂 A', 'TEST 原料 B'].map((v) => ({ value: v, label: v }))
const categoryOptions = ['新产品 / 工艺验证类', '年度持续稳定性考察类'].map((v) => ({ value: v, label: v }))

function show() {
  open.value = true
}
defineExpose({ show })

function saveDraft() {
  open.value = false
  message.success('原型入口：通知单草稿未落库，正式动作需由受控业务方法完成')
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
