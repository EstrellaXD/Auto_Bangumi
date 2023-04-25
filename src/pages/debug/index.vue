<script setup lang="ts">
import 'element-plus/es/components/message/style/css';
import 'element-plus/es/components/message-box/style/css';
import { ElMessage, ElMessageBox } from 'element-plus';
import { resetRule } from '@/api/debug';
import { appRestart } from '@/api/program';

const loading = ref(false);
async function reset() {
  loading.value = true;
  const res = await resetRule();
  loading.value = false;
  if (res.data === 'Success') {
    ElMessage({
      message: '数据已重置, 建议重启程序或容器',
      type: 'success',
    });
  } else {
    ElMessage({
      message: `错误: ${res.data}`,
      type: 'error',
    });
  }
}

function restart() {
  ElMessageBox.confirm('该操作将重启程序!', {
    type: 'warning',
  })
    .then(async () => {
      appRestart()
        .then(({ data }) => {
          console.log('🚀 ~ file: index.vue:33 ~ .then ~ data:', data);

          if (data.status === 'success') {
            ElMessage({
              message: '正在重启, 请稍后刷新页面...',
              type: 'success',
            });
          }
        })
        .catch((error) => {
          console.error('🚀 ~ file: index.vue:41 ~ .then ~ e:', error);
          ElMessage({
            message: '操作失败, 请重试!',
            type: 'error',
          });
        });
    })
    .catch(() => {});
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
            <el-button type="danger" :loading="loading" @click="reset"
              >重置</el-button
            >
          </div>
        </el-card>
      </el-col>
      <!-- E 重置数据 -->

      <!-- S 重启程序 -->
      <el-col :xs="24" :sm="12" :lg="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>重启程序</span>
            </div>
          </template>

          <div class="card-con">
            <el-button type="danger" :loading="loading" @click="restart"
              >重启</el-button
            >
          </div>
        </el-card>
      </el-col>
      <!-- E 重启程序 -->
    </el-row>
  </section>
</template>
