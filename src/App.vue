<script setup lang="ts">
import zhCn from 'element-plus/lib/locale/lang/zh-cn';
</script>

<template>
  <Suspense>
    <el-config-provider :locale="zhCn">
      <RouterView />
    </el-config-provider>
  </Suspense>
</template>
