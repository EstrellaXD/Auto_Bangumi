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
    <div rounded-10px overflow-hidden>
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

      <div bg-white px-8px py-20px>
        <DisclosurePanel>
          <slot name="top"></slot>
        </DisclosurePanel>

        <div line my-12px></div>

        <DisclosurePanel>
          <slot></slot>
        </DisclosurePanel>
      </div>
    </div>
  </Disclosure>
</template>
