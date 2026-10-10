<template>
  <div class="iam-assignments">
    <div v-for="(position, index) in demo.personPositions({ positionIds })" :key="position.id" class="iam-assignment-summary">
      <strong>{{ demo.departmentName(position.departmentId) }} / {{ position.name }}</strong>
      <small>{{ index ? '兼任' : '主岗' }}</small>
      <div class="iam-tags">
        <span v-for="role in demo.data.roles.filter(item => position.roleIds.includes(item.id))" :key="role.id" class="iam-role-tag">{{ role.name }}</span>
        <span v-if="!position.roleIds.length" class="iam-muted">未关联角色</span>
      </div>
      <p v-if="showScope" class="iam-note">数据范围：{{ position.scopeLabel }}</p>
    </div>
    <span v-if="!demo.personPositions({ positionIds }).length" class="iam-muted">选择部门与岗位后，自动显示对应角色</span>
  </div>
</template>
<script setup lang="ts">
import { usePeopleAccessDemoStore } from '@/stores/peopleAccessDemo'
defineProps<{ positionIds: string[]; showScope?: boolean }>()
const demo = usePeopleAccessDemoStore()
</script>
