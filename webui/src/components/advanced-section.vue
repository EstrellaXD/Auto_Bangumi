<script lang="ts" setup>
import { ChevronDown } from '@lucide/vue';

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
      <ChevronDown
        class="advanced-chevron"
        :class="{ 'advanced-chevron--open': open }"
        :size="14"
      />
      {{ $t('search.confirm.advanced') }}
    </button>

    <!-- 0fr↔1fr 行高过渡：高度可插值，展开/收起不再一帧跳到终值；
         收起时 inert，隐藏的控件不可聚焦 -->
    <div class="advanced-collapse" :class="{ 'is-open': open }">
      <div class="advanced-inner" :inert="!open">
        <div class="advanced-content">
          <slot />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
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

.advanced-collapse {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transition: grid-template-rows var(--transition-normal),
    opacity var(--transition-normal);

  &.is-open {
    grid-template-rows: 1fr;
    opacity: 1;
  }

  @media (prefers-reduced-motion: reduce) {
    transition: none;
  }
}

.advanced-inner {
  min-height: 0;
  overflow: hidden;
}

.advanced-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-top: 8px;
}
</style>
