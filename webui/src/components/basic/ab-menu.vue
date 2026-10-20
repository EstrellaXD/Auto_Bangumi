<script lang="ts" setup>
import { cloneVNode, h } from 'vue';
import type { Component, VNode } from 'vue';
import { NDropdown } from 'naive-ui';
import type { DropdownOption } from 'naive-ui';

export interface AbMenuItem {
  key?: string | number;
  label: string | (() => string);
  icon?: Component;
  danger?: boolean;
  disabled?: boolean;
  handler?: () => void | Promise<void>;
}

// 下拉菜单：naive-ui NDropdown 负责定位与键盘导航（方向键/回车/Esc）；
// 触发器放在 #trigger 插槽。NDropdown 不输出 aria，menuitem 角色与
// 触发器的 aria-haspopup/aria-expanded 在这里补上。
const { items, align = 'left' } = defineProps<{
  items: AbMenuItem[];
  /** 菜单相对触发器的对齐边 */
  align?: 'left' | 'right';
}>();

const emit = defineEmits<{ select: [item: AbMenuItem] }>();

const slots = defineSlots<{ trigger: () => VNode[] }>();

const open = ref(false);

const options = computed<DropdownOption[]>(() =>
  items.map((item, index) => ({
    key: item.key ?? index,
    label: item.label,
    disabled: item.disabled,
    icon: item.icon && (() => h(item.icon!, { size: 15 })),
    props: {
      role: 'menuitem',
      class: item.danger ? 'ab-menu-item--danger' : undefined,
    },
  }))
);

function Trigger() {
  return cloneVNode(slots.trigger()[0], {
    'aria-haspopup': 'menu',
    'aria-expanded': open.value,
  });
}

function onSelect(key: string | number) {
  const item = items.find((entry, index) => (entry.key ?? index) === key);
  if (!item || item.disabled) return;
  item.handler?.();
  emit('select', item);
}
</script>

<template>
  <NDropdown
    trigger="click"
    :show="open"
    :options="options"
    :placement="align === 'right' ? 'bottom-end' : 'bottom-start'"
    :menu-props="() => ({ class: 'ab-menu-list' })"
    @update:show="open = $event"
    @select="onSelect"
  >
    <Trigger />
  </NDropdown>
</template>

<!-- 不加 scoped：菜单项由 NDropdown 渲染并传送到 body，scoped 选择器命中不了。
     改写 naive-ui 的颜色变量，悬停态也保持危险色。 -->
<style lang="scss">
.ab-menu-item--danger {
  --n-option-text-color: var(--color-danger);
  --n-option-text-color-hover: var(--color-danger);
  --n-prefix-color: var(--color-danger);
}

.ab-menu-list {
  min-width: 180px;

  // 触屏放大命中区域，与旧菜单一致
  @include forTouch {
    .n-dropdown-option-body {
      --n-option-height: var(--touch-target);
    }
  }
}
</style>
