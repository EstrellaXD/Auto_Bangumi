<script lang="ts" setup>
import { Down, Up } from '@icon-park/vue-next';
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue';

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
      <DisclosureButton class="fold-panel-header">
        <div class="fold-panel-title">{{ title }}</div>
        <Component :is="open ? Up : Down" :size="14" />
      </DisclosureButton>

      <DisclosurePanel>
        <div class="fold-panel-body">
          <slot></slot>
        </div>
      </DisclosurePanel>
    </div>
  </Disclosure>
</template>

<style lang="scss" scoped>
.fold-panel {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: border-color var(--transition-normal);
}

.fold-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 14px;
  height: 34px;
  background: transparent;
  color: var(--color-text-secondary);
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: color var(--transition-normal),
              border-color var(--transition-normal);
}

.fold-panel-title {
  font-size: 15px;
  font-weight: 600;
}

.fold-panel-body {
  background: var(--color-surface);
  padding: 12px 14px;
  font-size: 14px;
  color: var(--color-text);
  transition: background-color var(--transition-normal),
              color var(--transition-normal);
}
</style>
