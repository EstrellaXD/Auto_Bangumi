<script lang="ts" setup>
defineProps<{
  label: string;
}>();
</script>

<template>
  <el-col :xs="24" :sm="12" :md="8">
    <el-form-item :label="label">
      <slot></slot>
    </el-form-item>
  </el-col>
</template>
