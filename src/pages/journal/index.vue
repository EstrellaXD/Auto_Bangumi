<script setup lang="ts">
import { getABLog } from '@/api/debug';

const log = ref(null);
const timer = ref<number | null>(null);

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
  <div class="log-box" wh-full overflow-hidden px-2em leading-2em>
    <pre whitespace-break-spaces>{{ log }}</pre>
  </div>
</template>
