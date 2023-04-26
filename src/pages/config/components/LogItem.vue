<script lang="ts" setup>
import { form, tfOptions } from '../form-data';

const log = computed(() => form.log);
</script>

<template>
  <ConfigFormRow title="日志">
    <ConfigFormCol label="启用debug">
      <el-select v-model="log.debug_enable" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>
  </ConfigFormRow>
</template>
