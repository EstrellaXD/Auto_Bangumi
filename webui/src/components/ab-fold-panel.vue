<script lang="ts" setup>
import { ChevronDown } from '@lucide/vue';
import { NCollapse, NCollapseItem } from 'naive-ui';

// 折叠面板 v2：naive-ui NCollapse 负责展开状态与高度动画（reduced-motion 下由全局规则直接切换）。
// NCollapse 的头部是无语义的 div，可聚焦的 button 与 aria-expanded 由插槽提供；
// 点击冒泡到 naive-ui 的头部触发切换。正文始终挂载（display-directive="show"）。
const { title = 'title', defaultOpen = true } = defineProps<{
  title: string;
  defaultOpen?: boolean;
}>();
</script>

<template>
  <NCollapse
    class="fold-panel"
    display-directive="show"
    :default-expanded-names="defaultOpen ? ['panel'] : []"
  >
    <NCollapseItem name="panel">
      <template #header="{ collapsed }">
        <button
          type="button"
          class="fold-panel-header"
          :class="{ 'fold-panel-header--open': !collapsed }"
          :aria-expanded="!collapsed"
        >
          <div class="fold-panel-title">
            {{ title }}
          </div>
          <slot name="extra" />
          <ChevronDown
            class="fold-panel-chevron"
            :class="{ 'fold-panel-chevron--open': !collapsed }"
            :size="14"
          />
        </button>
      </template>
      <template #arrow>
        <span />
      </template>

      <div class="fold-panel-body">
        <slot />
      </div>
    </NCollapseItem>
  </NCollapse>
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

// naive-ui 的箭头与正文上边距不用：箭头画在 button 里，间距由 body 自己给
.fold-panel :deep(.n-collapse-item-arrow) {
  display: none;
}

// naive-ui 的选择器带三层祖先类，这里写全才能压过
.fold-panel
  :deep(
    .n-collapse-item .n-collapse-item__content-wrapper .n-collapse-item__content-inner
  ) {
  padding-top: 0;
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
  .fold-panel-chevron {
    transition: none;
  }
}
</style>
