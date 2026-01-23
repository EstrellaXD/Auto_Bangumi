<script lang="ts" setup>
import { Switch } from '@headlessui/vue';

withDefaults(
  defineProps<{
    small?: boolean;
  }>(),
  {
    small: false,
  }
);

const checked = defineModel<boolean>({ default: false });
</script>

<template>
  <Switch v-model="checked" as="template">
    <div class="checkbox-wrapper">
      <slot name="before"></slot>

      <div
        class="checkbox"
        :class="[
          small ? 'checkbox--small' : 'checkbox--normal',
          checked && 'checkbox--checked',
        ]"
      >
        <div
          class="checkbox-inner"
          :class="[
            small ? 'checkbox-inner--small' : 'checkbox-inner--normal',
            checked && 'checkbox-inner--checked',
          ]"
        ></div>
      </div>

      <slot name="after"></slot>
    </div>
  </Switch>
</template>

<style lang="scss" scoped>
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.checkbox {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border: 2px solid var(--color-primary);
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast);

  &--normal {
    width: 24px;
    height: 24px;
    border-radius: var(--radius-sm);
    border-width: 2px;
  }

  &--small {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border-width: 2px;
  }

  &--checked {
    border-color: var(--color-primary);
  }

  &:hover:not(.checkbox--checked) {
    .checkbox-inner {
      background: var(--color-border-hover);
    }
  }
}

.checkbox-inner {
  border-radius: 2px;
  transition: background-color var(--transition-fast);
  background: transparent;

  &--normal {
    width: 12px;
    height: 12px;
  }

  &--small {
    width: 8px;
    height: 8px;
  }

  &--checked {
    background: var(--color-primary);
  }
}
</style>
