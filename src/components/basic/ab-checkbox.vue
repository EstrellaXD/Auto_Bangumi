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
    <div flex items-center space-x-8px is-btn>
      <slot name="before"></slot>

      <div
        rounded-4px
        rel
        f-cer
        bg-white
        border="3px #3c239f"
        :class="[small ? 'wh-16px' : 'wh-32px', !checked && 'group']"
      >
        <div
          rounded-2px
          transition-all
          duration-300
          :class="[
            small ? 'wh-8px' : 'wh-16px',
            checked ? 'bg-[#3c239f]' : 'bg-transparent',
          ]"
          group-hover:bg="#cccad4"
          group-active:bg="#3c239f"
        ></div>
      </div>

      <slot name="after"></slot>
    </div>
  </Switch>
</template>
