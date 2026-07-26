<script lang="ts" setup>
import { Down } from '@icon-park/vue-next';

/** v-model open state */
const open = defineModel<boolean>('open', { default: false });
</script>

<template>
  <div class="advanced-section">
    <button
      type="button"
      class="advanced-toggle"
      :aria-expanded="open"
      @click="open = !open"
    >
      <Down
        class="advanced-chevron"
        :class="{ 'advanced-chevron--open': open }"
        theme="outline"
        size="14"
      />
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

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }
}

.advanced-chevron {
  transform: rotate(-90deg);
  transition: transform var(--transition-normal);

  &--open {
    transform: rotate(0deg);
  }

  @media (prefers-reduced-motion: reduce) {
    transition: none;
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

@media screen and (max-width: 639px) {
  .advanced-toggle {
    width: 100%;
    min-height: var(--touch-target);
  }

  .advanced-content {
    padding: 12px;
  }
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
