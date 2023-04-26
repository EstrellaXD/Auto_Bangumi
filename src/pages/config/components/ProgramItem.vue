<script lang="ts" setup>
import { form } from '../form-data';

const program = computed(() => form.program);
</script>

<template>
  <ConfigFormRow title="主程序">
    <ConfigFormCol label="RSS 检查间隔">
      <el-input v-model.number="program.sleep_time" type="number" />
    </ConfigFormCol>

    <ConfigFormCol label="重命名间隔">
      <el-input v-model.number="program.rename_times" type="number" />
    </ConfigFormCol>

    <ConfigFormCol label="webui端口" prop="program.webui_port">
      <el-input v-model.number="program.webui_port" type="number" />
    </ConfigFormCol>
  </ConfigFormRow>
</template>
