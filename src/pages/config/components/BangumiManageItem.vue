<script lang="ts" setup>
import { form, renameMethod, tfOptions } from '../form-data';

const bgmManage = computed(() => form.bangumi_manage);
</script>

<template>
  <ConfigFormRow title="番剧管理">
    <ConfigFormCol label="启用">
      <el-select v-model="bgmManage.enable" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="历史番剧下载">
      <el-select v-model="bgmManage.eps_complete" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="重命名方法">
      <el-select v-model="bgmManage.rename_method" flex-1>
        <el-option
          v-for="opt in renameMethod"
          :key="opt"
          :label="opt"
          :value="opt"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="下载规则中添加组名">
      <el-select v-model="bgmManage.group_tag" flex-1>
        <el-option
          v-for="(opt, index) in tfOptions"
          :key="index"
          :label="opt.label"
          :value="opt.value"
        ></el-option>
      </el-select>
    </ConfigFormCol>

    <ConfigFormCol label="删除坏种">
      <el-select v-model="bgmManage.remove_bad_torrent" flex-1>
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
