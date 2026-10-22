<script lang="ts" setup>
import { CirclePlus, Cog, Languages } from '@lucide/vue';
import type { Component } from 'vue';
import AbMenu from './basic/ab-menu.vue';
import type { AbMenuItem } from './basic/ab-menu.vue';

const { running = false, items } = defineProps<{
  running: boolean;
  items: {
    id: number;
    icon: Component;
    label: string | (() => string);
    handle?: () => void | Promise<void>;
  }[];
}>();

defineEmits<{
  (e: 'changeLang'): void;
  (e: 'clickAdd'): void;
}>();

// 系统菜单复用 ab-menu（naive-ui NDropdown）
const menuItems = computed<AbMenuItem[]>(() =>
  items.map((i) => ({
    key: i.id,
    label: i.label,
    icon: i.icon,
    handler: i.handle,
  }))
);
</script>

<template>
  <div class="status-bar">
    <div class="status-bar-actions">
      <button
        class="status-bar-btn"
        aria-label="Switch language"
        @click="() => $emit('changeLang')"
      >
        <Languages :size="18" />
      </button>

      <button
        class="status-bar-btn"
        aria-label="Add RSS subscription"
        @click="() => $emit('clickAdd')"
      >
        <CirclePlus :size="18" />
      </button>

      <AbMenu :items="menuItems" align="right">
        <template #trigger>
          <button class="status-bar-btn" aria-label="System menu">
            <Cog :size="18" />
          </button>
        </template>
      </AbMenu>

      <ab-status :state="running ? 'running' : 'stopped'" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.status-bar {
  position: relative;
}

.status-bar-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 18px;
}

.status-bar-btn {
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast),
    background-color var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  // Ensure minimum touch target
  min-width: 36px;
  min-height: 36px;
  padding: 6px;
  border-radius: var(--radius-sm);

  // Transparent background — a full 44px hit area costs nothing visually.
  // 仅触屏放大命中区域；桌面指针设备保持 36px 紧凑排布。
  @include forTouch {
    min-width: var(--touch-target);
    min-height: var(--touch-target);
  }

  // 与 ab-icon-button ghost 一致：状态只靠底色与墨色表达
  &:hover {
    background: var(--color-surface-2);
    color: var(--color-text);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}
</style>
