<script lang="ts" setup>
import { form } from '../form-data';

const program = computed(() => form.program);
</script>

<template>
  <ConfigFormRow title="主程序">
    <ConfigFormCol label="RSS 检查间隔">
      <el-input v-model="program.sleep_time" type="number" />
    </ConfigFormCol>

    <ConfigFormCol label="重命名间隔">
      <el-input v-model="program.rename_times" type="number" />
    </ConfigFormCol>

    <ConfigFormCol label="webui端口">
      <el-input v-model="program.webui_port" type="number" />
    </ConfigFormCol>
  </ConfigFormRow>
</template>
