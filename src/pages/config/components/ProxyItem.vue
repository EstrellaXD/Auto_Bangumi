<script lang="ts" setup>
import { form, proxyType, tfOptions } from '../form-data';

const proxy = computed(() => form.proxy);
</script>

<template>
  <ConfigFormRow title="代理">
    <ConfigFormCol label="启用">
      <el-select v-model="proxy.enable" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="代理类型">
      <el-select v-model="proxy.type" flex-1>
        <el-option
          v-for="opt in proxyType"
          :key="opt"
          :label="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="host">
      <el-input v-model="proxy.host"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="port">
      <el-input v-model="proxy.port" type="number"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="username">
      <el-input v-model="proxy.username"></el-input>
    </ConfigFormCol>

    <ConfigFormCol label="password">
      <el-input v-model="proxy.password"></el-input>
    </ConfigFormCol>
  </ConfigFormRow>
</template>
