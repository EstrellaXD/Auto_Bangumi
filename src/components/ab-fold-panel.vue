<script lang="ts" setup>
import { Down, Up } from '@icon-park/vue-next';
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue';

const props = withDefaults(
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
    <div rounded-10px overflow-hidden h-max>
      <DisclosureButton
        bg-theme-row
        w-full
        text-white
        fx-cer
        px-20px
        h-45px
        justify-between
      >
        <div text-h2>{{ title }}</div>

        <Component :is="open ? Up : Down" size="24" />
      </DisclosureButton>

      <div bg-white py-20px :class="[open ? 'px-20px' : 'px-8px']">
        <div line my-12px v-show="!open"></div>

        <DisclosurePanel>
          <slot></slot>
        </DisclosurePanel>
      </div>
    </div>
  </Disclosure>
</template>
