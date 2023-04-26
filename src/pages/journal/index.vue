<script setup lang="ts">
const store = logStore();

onActivated(() => {
  store.get();
  store.onUpdate();
});

onDeactivated(() => {
  store.removeUpdate();
});
</script>

<template>
  <div class="log-box" wh-full overflow-hidden px-2em leading-2em text-12px>
    <pre whitespace-break-spaces>{{ store.log }}</pre>
  </div>
</template>
