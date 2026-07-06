<script lang="ts" setup>
import { Down } from '@icon-park/vue-next';
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue';

// 折叠面板 v2：headlessui 提供键盘/aria-expanded；
// 旋转箭头 + grid-rows 高度动画（reduced-motion 下直接切换）。
withDefaults(
  defineProps<{
    title: string;
    defaultOpen?: boolean;
  }>(),
  {
    title: 'title',
    defaultOpen: true,
  }
);
</script>

<template>
  <Disclosure v-slot="{ open }" :default-open="defaultOpen">
    <div class="fold-panel">
      <DisclosureButton
        class="fold-panel-header"
        :class="{ 'fold-panel-header--open': open }"
      >
        <div class="fold-panel-title">{{ title }}</div>
        <slot name="extra"></slot>
        <Down
          class="fold-panel-chevron"
          :class="{ 'fold-panel-chevron--open': open }"
          :size="14"
        />
      </DisclosureButton>

      <div class="fold-panel-collapse" :class="{ 'is-open': open }">
        <div class="fold-panel-clip">
          <DisclosurePanel static>
            <div class="fold-panel-body">
              <slot></slot>
            </div>
          </DisclosurePanel>
        </div>
      </div>
    </div>
  </Disclosure>
</template>

<style lang="scss" scoped>
.fold-panel {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: border-color var(--transition-normal);
  min-width: 0; // Allow panel to shrink below content size
  max-width: 100%;
  overflow: hidden;
}

.fold-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 0 14px;
  height: 34px;
  background: transparent;
  color: var(--color-text-secondary);
  border: none;
  border-bottom: 1px solid transparent;
  cursor: pointer;
  transition: color var(--transition-normal),
    border-color var(--transition-normal);

  @include forTouch {
    height: var(--touch-target);
  }

  &:hover {
    color: var(--color-text);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
    border-radius: var(--radius-sm);
  }

  &--open {
    border-bottom-color: var(--color-border);
  }
}

.fold-panel-title {
  flex: 1;
  text-align: left;
  font-size: 15px;
  font-weight: 600;
}

.fold-panel-chevron {
  flex-shrink: 0;
  transition: transform var(--transition-normal);

  &--open {
    transform: rotate(180deg);
  }
}

// grid-rows 高度动画：0fr ↔ 1fr（不动画 height 本身）
.fold-panel-collapse {
  display: grid;
  grid-template-rows: 0fr;
  visibility: hidden;
  transition: grid-template-rows var(--transition-normal),
    visibility 0s var(--transition-normal);

  &.is-open {
    grid-template-rows: 1fr;
    visibility: visible;
    transition: grid-template-rows var(--transition-normal), visibility 0s;
  }
}

.fold-panel-clip {
  min-height: 0;
  overflow: hidden;
}

.fold-panel-body {
  background: var(--color-surface);
  padding: 12px 14px;
  font-size: 14px;
  color: var(--color-text);
  overflow-x: hidden;
  transition: background-color var(--transition-normal),
    color var(--transition-normal);
}

@media (prefers-reduced-motion: reduce) {
  .fold-panel-collapse,
  .fold-panel-chevron {
    transition: none;
  }
}
</style>
