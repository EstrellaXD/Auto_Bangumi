<script lang="ts" setup>
import { form, notificationType, tfOptions } from '../form-data';

const notification = computed(() => form.notification);
</script>

<template>
  <ConfigFormRow title="通知">
    <ConfigFormCol label="启用">
      <el-select v-model="notification.enable" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="通知类型">
      <el-select v-model="notification.type" flex-1>
        <el-option
          v-for="opt in notificationType"
          :key="opt"
          :label="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="token">
      <el-input v-model="notification.token"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="chat_id">
      <el-input v-model="notification.chat_id" type="number"></el-input>
    </ConfigFormCol>
  </ConfigFormRow>
</template>
