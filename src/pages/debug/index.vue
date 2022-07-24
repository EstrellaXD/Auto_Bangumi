<script setup lang="ts">
import { resetRule } from '@/api/debug';
import 'element-plus/es/components/message/style/css'
import { ElMessage } from 'element-plus'

const loading = ref(false);
const reset = async () => {
  const res = await resetRule();
  if (res.data === "Success") {
    ElMessage({
      message: '数据已重置, 建议重启容器',
      type: 'success',
    })
  } else {
    ElMessage({
      message: `错误: ${res.data}`,
      type: 'error',
    })
  }
}
</script>

<template>
  <section class="debug">
    <el-row :gutter="20">

      <!-- S 重置数据 -->
      <el-col :xs="24" :sm="12" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>重置AB数据</span>
            </div>
          </template>

          <div class="card-con">
            <el-button
              type="danger"
              :loading="loading"
              @click="reset"
            >重置</el-button>
          </div>

        </el-card>
      </el-col>
      <!-- E 重置数据 -->

    </el-row>
  </section>
</template>

<style lang='scss' scope>
</style>