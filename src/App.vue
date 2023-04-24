<script setup lang="ts">
import zhCn from 'element-plus/lib/locale/lang/zh-cn';
import { IconConfigProvider } from '@vicons/utils';
</script>

<template>
  <Suspense>
    <el-config-provider :locale="zhCn">
      <IconConfigProvider size="18">
        <RouterView />
      </IconConfigProvider>
    </el-config-provider>
  </Suspense>
</template>
