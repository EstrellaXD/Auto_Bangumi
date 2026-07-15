<script lang="ts" setup>
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue';
import type { Component } from 'vue';

export interface AbMenuItem {
  key?: string | number;
  label: string | (() => string);
  icon?: Component;
  danger?: boolean;
  disabled?: boolean;
  handler?: () => void | Promise<void>;
}

// 下拉菜单：headlessui Menu 负责键盘导航与 aria；
// 触发器放在 #trigger 插槽（渲染为 MenuButton）。
withDefaults(
  defineProps<{
    items: AbMenuItem[];
    /** 菜单相对触发器的对齐边 */
    align?: 'left' | 'right';
    /** 菜单相对触发器的展开方向 */
    placement?: 'bottom' | 'top';
  }>(),
  {
    align: 'left',
    placement: 'bottom',
  }
);

const emit = defineEmits<{ select: [item: AbMenuItem] }>();

function itemLabel(item: AbMenuItem): string {
  return typeof item.label === 'function' ? item.label() : item.label;
}

function onSelect(item: AbMenuItem) {
  if (item.disabled) return;
  item.handler?.();
  emit('select', item);
}
</script>

<template>
  <Menu as="div" class="ab-menu">
    <MenuButton as="template">
      <slot name="trigger"></slot>
    </MenuButton>

    <MenuItems
      class="ab-menu-list"
      :class="[`ab-menu-list--${align}`, `ab-menu-list--${placement}`]"
    >
      <MenuItem
        v-for="(item, index) in items"
        :key="item.key ?? index"
        v-slot="{ active }"
        :disabled="item.disabled"
      >
        <button
          type="button"
          class="ab-menu-item"
          :class="[
            active && 'ab-menu-item--active',
            item.danger && 'ab-menu-item--danger',
            item.disabled && 'ab-menu-item--disabled',
          ]"
          @click="onSelect(item)"
        >
          <Component :is="item.icon" v-if="item.icon" :size="15"></Component>
          <span class="ab-menu-item-label">{{ itemLabel(item) }}</span>
        </button>
      </MenuItem>
    </MenuItems>
  </Menu>
</template>

<!-- Headless UI owns the rendered Menu roots, so scoped attributes do not
     reliably reach them. The ab-menu prefix keeps these global rules isolated. -->
<style lang="scss">
.ab-menu {
  position: relative;
  display: inline-flex;
}

.ab-menu-list {
  position: absolute;
  top: 100%;
  margin-top: 4px;
  z-index: var(--z-popover);
  min-width: 180px;
  padding: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);

  &--left {
    left: 0;
  }

  &--right {
    right: 0;
  }

  &--top {
    top: auto;
    bottom: 100%;
    margin-top: 0;
    margin-bottom: 4px;
  }

  &:focus-visible {
    outline: none;
  }
}

.ab-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background-color var(--transition-fast);

  @include forTouch {
    padding: 11px 10px;
  }

  // active 由 headlessui 的键盘/悬停导航驱动
  &--active {
    background: var(--color-surface-2);
  }

  &--danger {
    color: var(--color-danger);
  }

  &--disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}

.ab-menu-item-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media screen and (max-width: 639px) {
  .ab-menu-item {
    min-height: 44px;
    padding: 10px;
  }
}
</style>
