<template>
  <section class="preview-explanation glass-surface">
    <span class="page-kicker">PORTAL 展示预览</span>
    <h1>这里保留现有 Portal 导航位置</h1>
    <p>本次展示人员信息与权限管理的组合设计，其他入口在此预览中只展示位置。</p>
    <a-button type="primary" @click="$router.push('/hbos/admin/people')">查看人员与权限</a-button>
  </section>
</template>
<style scoped>.preview-explanation{padding:36px;border-radius:24px;margin-top:20px}.preview-explanation h1{font-size:24px;font-weight:600;margin:14px 0}.preview-explanation p{color:#72829d;margin-bottom:24px}</style>
