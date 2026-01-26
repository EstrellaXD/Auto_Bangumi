<script lang="ts" setup>
withDefaults(
  defineProps<{
    running: boolean;
    size?: string;
  }>(),
  {
    running: false,
    size: '1em',
  }
);
</script>

<template>
  <div
    class="status-indicator"
    :style="{ width: size, height: size }"
    role="status"
    :aria-label="running ? 'System running' : 'System stopped'"
  >
    <div class="status-ring">
      <div
        class="status-dot"
        :class="[running ? 'status-dot--running' : 'status-dot--stopped']"
      ></div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-ring {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  transition: border-color var(--transition-normal);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  transition: background-color var(--transition-fast);

  &--running {
    background: var(--color-success);
    box-shadow: 0 0 6px color-mix(in srgb, var(--color-success) 40%, transparent);
    animation: pulse 2s ease-in-out infinite;
  }

  &--stopped {
    background: var(--color-danger);
    box-shadow: 0 0 6px color-mix(in srgb, var(--color-danger) 40%, transparent);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
</style>
