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
// 触发器放在 #trigger 插槽。NDropdown 不输出 aria，也不移动焦点：这里补上
// menu/menuitem 角色、触发器的 aria-haspopup/aria-expanded，打开时把焦点
// 移到菜单容器，并用 aria-activedescendant 指向高亮项，读屏才能读出当前项。
const { items, align = 'left' } = defineProps<{
  items: AbMenuItem[];
  /** 菜单相对触发器的对齐边 */
  align?: 'left' | 'right';
}>();

const emit = defineEmits<{ select: [item: AbMenuItem] }>();

const slots = defineSlots<{ trigger: () => VNode[] }>();

const open = ref(false);
const listId = useId();
const activeId = ref<string>();

const options = computed<DropdownOption[]>(() =>
  items.map((item, index) => ({
    key: item.key ?? index,
    label: item.label,
    disabled: item.disabled,
    icon: item.icon && (() => h(item.icon!, { size: 15 })),
    props: {
      id: `${listId}-${item.key ?? index}`,
      role: 'menuitem',
      'aria-disabled': item.disabled || undefined,
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

// NDropdown 不暴露高亮项，只能从它的 --pending 类读出
let observer: MutationObserver | undefined;
let opener: HTMLElement | null = null;

watch(open, async (isOpen) => {
  observer?.disconnect();
  activeId.value = undefined;
  const list = document.getElementById(listId);
  if (!isOpen) {
    // 焦点留在正在关闭的菜单里或已丢到 body 时，还给触发器
    const focused = document.activeElement;
    if (focused === document.body || list?.contains(focused)) opener?.focus();
    return;
  }
  opener = document.activeElement as HTMLElement | null;
  await nextTick();
  const menu = document.getElementById(listId);
  if (!menu) return;
  menu.focus({ preventScroll: true });
  observer = new MutationObserver(() => {
    activeId.value =
      menu.querySelector('.n-dropdown-option-body--pending')?.id || undefined;
  });
  observer.observe(menu, {
    subtree: true,
    attributes: true,
    attributeFilter: ['class'],
  });
});

onBeforeUnmount(() => observer?.disconnect());

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
    :menu-props="
      () => ({
        'id': listId,
        'class': 'ab-menu-list',
        'role': 'menu',
        'tabindex': -1,
        'aria-activedescendant': activeId,
      })
    "
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

  // 焦点在容器上只为 aria-activedescendant，高亮项已经标出当前项
  &:focus {
    outline: none;
  }

  // 触屏放大命中区域，与旧菜单一致
  @include forTouch {
    .n-dropdown-option-body {
      --n-option-height: var(--touch-target);
    }
  }
}
</style>
