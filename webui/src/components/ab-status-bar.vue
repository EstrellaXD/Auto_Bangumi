<script lang="ts" setup>
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue';
import { AddOne, International, System } from '@icon-park/vue-next';

withDefaults(
  defineProps<{
    running: boolean;
    items: {
      id: number;
      icon: any;
      label: string | (() => string);
      handle?: () => void | Promise<void>;
    }[];
  }>(),
  {
    running: false,
  }
);

defineEmits<{
  (e: 'changeLang'): void;
  (e: 'clickAdd'): void;
}>();

function abLabel(label: string | (() => string)) {
  if (typeof label === 'function') {
    return label();
  } else {
    return label;
  }
}
</script>

<template>
  <Menu>
    <div class="status-bar">
      <div class="status-bar-actions">
        <button
          class="status-bar-btn"
          aria-label="Switch language"
          @click="() => $emit('changeLang')"
        >
          <International theme="outline" size="1em" />
        </button>

        <button
          class="status-bar-btn"
          aria-label="Add RSS subscription"
          @click="() => $emit('clickAdd')"
        >
          <AddOne theme="outline" size="1em" />
        </button>

        <MenuButton class="status-bar-btn" aria-label="System menu">
          <System theme="outline" size="1em" />
        </MenuButton>

        <ab-status :running="running" />
      </div>

      <MenuItems class="status-menu">
        <MenuItem v-for="i in items" :key="i.id" v-slot="{ active }">
          <div
            class="status-menu-item"
            :class="[active && 'status-menu-item--active']"
            @click="() => i.handle && i.handle()"
          >
            <div class="status-menu-item-icon">
              <Component :is="i.icon" size="16"></Component>
            </div>
            <div class="status-menu-item-label">{{ abLabel(i.label) }}</div>
          </div>
        </MenuItem>
      </MenuItems>
    </div>
  </Menu>
</template>

<style lang="scss" scoped>
.status-bar {
  position: relative;
}

.status-bar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;

  @include forMobile {
    gap: 8px;
    font-size: 18px;
  }
}

.status-bar-btn {
  cursor: pointer;
  user-select: none;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast), transform var(--transition-fast);
  display: flex;
  align-items: center;
  background: transparent;
  border: none;
  padding: 4px;
  border-radius: var(--radius-sm);

  &:hover {
    color: var(--color-primary);
    transform: scale(1.1);
  }

  &:active {
    transform: scale(1);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.status-menu {
  position: absolute;
  top: 40px;
  right: 0;
  width: 160px;
  padding: 4px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  z-index: 50;
  overflow: hidden;
  animation: dropdown-in 150ms ease-out;
  transform-origin: top right;
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);

  @include forPC {
    top: 44px;
  }
}

@keyframes dropdown-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.status-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 32px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text);
  transition: color var(--transition-fast), background-color var(--transition-fast);

  &:hover,
  &--active {
    color: var(--color-primary);
    background: var(--color-primary-light);
  }
}

.status-menu-item-icon {
  color: var(--color-primary);
  display: flex;
  align-items: center;
}

.status-menu-item-label {
  font-size: 12px;
}
</style>
