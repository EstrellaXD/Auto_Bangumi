<script lang="ts" setup>
import { Switch } from '@headlessui/vue';

const checked = defineModel<boolean>('checked', {
  default: false,
});
</script>

<template>
  <Switch v-model="checked" as="template">
    <div class="switch-track" :class="{ 'switch-track--checked': checked }">
      <div
        class="switch-thumb"
        :class="{ 'switch-thumb--checked': checked }"
      ></div>
    </div>
  </Switch>
</template>

<style lang="scss" scoped>
.switch-track {
  width: 44px;
  height: 24px;
  border-radius: var(--radius-full);
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 2px;
  cursor: pointer;
  user-select: none;
  background: var(--color-border-hover);
  transition: background-color var(--transition-fast);

  &--checked {
    background: var(--color-primary);
  }
}

.switch-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform var(--transition-fast);

  &--checked {
    transform: translateX(20px);
  }
}
</style>
