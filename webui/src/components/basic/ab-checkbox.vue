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
        rel
        f-cer
        bg-white
        :class="[small ? 'wh-16px' : 'wh-32px', !checked && 'group']"
        :border="small ? '2px solid #3c239f' : '4px solid #3c239f'"
        :rounded="small ? '4px' : '6px'"
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
