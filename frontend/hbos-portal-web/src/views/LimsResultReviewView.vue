<template>
  <section class="product-page operational-page">
    <div class="operational-page-head">
      <div>
        <a-button type="text" class="back-link" @click="$router.push('/hbos/lims')">
          <ArrowLeftOutlined /> 返回工作台
        </a-button>
        <div class="page-kicker">LIMS · 结果复核</div>
        <div class="review-title-row">
          <h1>复核阿莫西林含量结果</h1>
          <a-tag color="processing">待复核</a-tag>
        </div>
        <p>RESULT-001 · SAMPLE-001 · 批次 26092401</p>
      </div>
      <a-space wrap>
        <a-button @click="sampleDrawerOpen = true"><InfoCircleOutlined /> 样品上下文</a-button>
        <a-button danger @click="rejectModalOpen = true">退回</a-button>
        <a-button type="primary" @click="confirmModalOpen = true">提交复核意见</a-button>
      </a-space>
    </div>

    <div class="review-layout">
      <div class="review-main-stack">
        <section class="operation-card glass-surface hbos-glass-g1">
          <div class="operation-card-head">
            <div><h2>检验结果</h2><p>复核原始结果与质量标准，不在 Portal 中直接批准。</p></div>
            <a-tag color="success">计算通过</a-tag>
          </div>

          <div class="result-summary-grid">
            <div><span>检验项目</span><strong>含量测定</strong></div>
            <div><span>结果</span><strong class="result-value">99.4%</strong></div>
            <div><span>规格</span><strong>98.0% – 102.0%</strong></div>
            <div><span>判定</span><strong class="tone-success">符合</strong></div>
          </div>

          <a-table :data-source="resultRows" :pagination="false" row-key="id" size="middle" class="operational-table" :scroll="{ x: 720 }">
            <a-table-column title="测定" data-index="name" key="name" width="150" />
            <a-table-column title="原始值" data-index="raw" key="raw" width="120" />
            <a-table-column title="计算结果" data-index="result" key="result" width="120" />
            <a-table-column title="规格" data-index="spec" key="spec" width="160" />
            <a-table-column title="判定" key="status" width="110">
              <template #default><a-tag color="success">符合</a-tag></template>
            </a-table-column>
          </a-table>
        </section>

        <section class="operation-card glass-surface hbos-glass-g1">
          <div class="operation-card-head">
            <div><h2>复核意见</h2><p>业务操作页采用 V1：稳定、低动效、清晰表单。</p></div>
          </div>
          <a-form layout="vertical">
            <a-form-item label="复核结论" required>
              <a-radio-group v-model:value="reviewConclusion">
                <a-radio-button value="approve">通过</a-radio-button>
                <a-radio-button value="return">退回分析员</a-radio-button>
              </a-radio-group>
            </a-form-item>
            <a-form-item label="复核意见">
              <a-textarea v-model:value="reviewComment" :rows="4" :maxlength="500" show-count placeholder="填写必要的复核说明" />
            </a-form-item>
          </a-form>
        </section>

        <section class="operation-card glass-surface hbos-glass-g1">
          <div class="operation-card-head">
            <div><h2>附件与原始记录</h2><p>这里只展示上下文；原始记录仍由 LIMS 业务对象管理。</p></div>
          </div>
          <div class="attachment-list">
            <button type="button"><FilePdfOutlined /><span><strong>含量测定原始记录.pdf</strong><small>2.4 MB · 分析员上传</small></span><EyeOutlined /></button>
            <button type="button"><FileExcelOutlined /><span><strong>仪器导出结果.xlsx</strong><small>128 KB · 系统附件</small></span><EyeOutlined /></button>
          </div>
        </section>
      </div>

      <aside class="review-context-stack">
        <section class="context-card glass-surface hbos-glass-g1">
          <h3>样品信息</h3>
          <dl>
            <div><dt>样品</dt><dd>SAMPLE-001</dd></div>
            <div><dt>物料</dt><dd>阿莫西林</dd></div>
            <div><dt>批次</dt><dd>26092401</dd></div>
            <div><dt>分析员</dt><dd>分析员 A</dd></div>
            <div><dt>提交时间</dt><dd>今天 14:36</dd></div>
          </dl>
        </section>

        <section class="context-card glass-surface hbos-glass-g1">
          <h3>职责分离</h3>
          <a-alert type="info" show-icon message="复核人与分析员必须不同" description="当前身份通过前端提示；真实提交时仍由 LIMS 后端再次执行 SoD 与状态校验。" />
        </section>

        <section class="context-card glass-surface hbos-glass-g1">
          <h3>活动记录</h3>
          <a-timeline>
            <a-timeline-item>14:36 · 分析员提交结果</a-timeline-item>
            <a-timeline-item>13:58 · 完成结果计算</a-timeline-item>
            <a-timeline-item>10:15 · 开始检验</a-timeline-item>
          </a-timeline>
        </section>
      </aside>
    </div>

    <a-drawer v-model:open="sampleDrawerOpen" title="样品上下文" width="560" root-class-name="hbos-context-drawer">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="样品编号">SAMPLE-001</a-descriptions-item>
        <a-descriptions-item label="物料">阿莫西林</a-descriptions-item>
        <a-descriptions-item label="批次">26092401</a-descriptions-item>
        <a-descriptions-item label="规格版本">SPEC-AMX-2026-03</a-descriptions-item>
        <a-descriptions-item label="来源">生产送检</a-descriptions-item>
      </a-descriptions>
      <a-divider />
      <h3>相关检验</h3>
      <a-list size="small" bordered :data-source="relatedTests">
        <template #renderItem="{ item }"><a-list-item>{{ item }}</a-list-item></template>
      </a-list>
    </a-drawer>

    <a-modal v-model:open="rejectModalOpen" title="退回复核结果" ok-text="确认退回" ok-type="danger" cancel-text="取消">
      <a-form layout="vertical"><a-form-item label="退回原因" required><a-textarea :rows="4" placeholder="请说明退回原因" /></a-form-item></a-form>
    </a-modal>

    <a-modal v-model:open="confirmModalOpen" title="提交复核意见" ok-text="确认提交" cancel-text="取消">
      <a-alert type="warning" show-icon message="正式功能接入后，此处将再次执行权限、状态、SoD 与电子签名策略。" />
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  ArrowLeftOutlined,
  EyeOutlined,
  FileExcelOutlined,
  FilePdfOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons-vue'

const sampleDrawerOpen = ref(false)
const rejectModalOpen = ref(false)
const confirmModalOpen = ref(false)
const reviewConclusion = ref('approve')
const reviewComment = ref('')

const resultRows = [
  { id: 'r1', name: '平行测定 1', raw: '0.4982', result: '99.3%', spec: '98.0% – 102.0%' },
  { id: 'r2', name: '平行测定 2', raw: '0.4991', result: '99.5%', spec: '98.0% – 102.0%' },
]

const relatedTests = ['有关物质 · 已完成', '水分 · 已完成', '鉴别 · 已完成']
</script>
