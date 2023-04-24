<script setup lang="ts">
import { getABLog } from '@/api/debug';

const log = ref(null);
const timer = ref<NodeJS.Timer | null>(null);

async function getLog() {
  const res = await getABLog();
  log.value = res.data;
}

function autoUpdate() {
  timer.value = setInterval(getLog, 5000);
}
getLog();

onMounted(autoUpdate);
onUnmounted(() => {
  clearInterval(Number(timer.value));
});
</script>

<template>
  <div class="log-box">
    <pre>{{ log }}</pre>
  </div>
</template>

<style lang="scss" scope>
.log-box {
  width: 100%;
  height: 100%;
  overflow: hidden;
  line-height: 2;
  padding: 0 2em;

  pre {
    white-space: break-spaces;
  }
}
</style>
