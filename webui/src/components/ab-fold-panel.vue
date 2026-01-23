<script lang="ts" setup>
import { Down, Up } from '@icon-park/vue-next';
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue';

withDefaults(
  defineProps<{
    title: string;
  }>(),
  {
    title: 'title',
  }
);
</script>

<template>
  <Disclosure v-slot="{ open }">
    <div class="fold-panel">
      <DisclosureButton class="fold-panel-header">
        <div class="fold-panel-title">{{ title }}</div>
        <Component :is="open ? Up : Down" :size="18" />
      </DisclosureButton>

      <div class="fold-panel-body" :class="[open && 'fold-panel-body--open']">
        <div v-show="!open" class="fold-panel-divider"></div>

        <DisclosurePanel>
          <slot></slot>
        </DisclosurePanel>
      </div>
    </div>
  </Disclosure>
</template>

<style lang="scss" scoped>
.fold-panel {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  transition: border-color var(--transition-normal);
}

.fold-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 20px;
  height: 42px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  cursor: pointer;

  @include forPC {
    height: 48px;
  }
}

.fold-panel-title {
  font-size: 16px;
  font-weight: 500;

  @include forPC {
    font-size: 18px;
  }
}

.fold-panel-body {
  background: var(--color-surface);
  padding: 10px 8px;
  font-size: 14px;
  color: var(--color-text);
  transition: background-color var(--transition-normal),
              color var(--transition-normal);

  &--open {
    padding: 16px 20px;
  }

  @include forPC {
    &--open {
      padding: 20px;
    }
  }
}

.fold-panel-divider {
  width: 100%;
  height: 1px;
  background: var(--color-border);
  margin: 12px 0;
}
</style>
