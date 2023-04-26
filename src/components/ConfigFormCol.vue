<script lang="ts" setup>
defineProps<{
  label: string;
  prop?: string | string[];
}>();
</script>

<template>
  <el-col :xs="24" :sm="12" :md="8" :lg="6" :xl="4">
    <el-form-item :label="label" :prop="prop ?? ''">
      <slot></slot>
    </el-form-item>
  </el-col>
</template>
