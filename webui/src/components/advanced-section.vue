<script lang="ts" setup>
import { Down, Right } from '@icon-park/vue-next';

/** v-model open state */
const open = defineModel<boolean>('open', { default: false });
</script>

<template>
  <div class="advanced-section">
    <button class="advanced-toggle" @click="open = !open">
      <component :is="open ? Down : Right" theme="outline" size="14" />
      {{ $t('search.confirm.advanced') }}
    </button>

    <Transition name="expand">
      <div v-show="open" class="advanced-content">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<style lang="scss" scoped>
.advanced-section {
  margin-bottom: 8px;
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color var(--transition-fast);

  &:hover {
    color: var(--color-text);
  }
}

.advanced-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-top: 8px;
}

// Expand transition
.expand-enter-active,
.expand-leave-active {
  transition: all var(--transition-normal);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
