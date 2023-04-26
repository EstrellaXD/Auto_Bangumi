<script lang="ts" setup>
defineProps<{
  title: string;
}>();
</script>

<template>
  <el-collapse-item>
    <template #title>
      <span font-bold text-base>{{ title }}</span>
    </template>

    <el-row :gutter="20">
      <slot></slot>
    </el-row>
  </el-collapse-item>
</template>
