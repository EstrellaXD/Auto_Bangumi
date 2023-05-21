<script lang="ts" setup>
import {
  TransitionRoot,
  TransitionChild,
  Dialog,
  DialogPanel,
} from '@headlessui/vue';

const props = withDefaults(
  defineProps<{
    show: boolean;
    title: string;
    maskClick: boolean;
  }>(),
  {
    show: false,
    title: 'title',
    maskClick: true,
  }
);

const emit = defineEmits(['update:show']);

const close = () => {
  if (props.maskClick) {
    emit('update:show', false);
  }
};
</script>

<template>
  <TransitionRoot appear :show="show" as="template">
    <Dialog as="div" @close="close" class="relative z-10">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black bg-opacity-25" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto">
        <div
          class="flex min-h-full items-center justify-center p-4 text-center"
        >
          <TransitionChild
            as="template"
            enter="duration-300 ease-out"
            enter-from="opacity-0 scale-95"
            enter-to="opacity-100 scale-100"
            leave="duration-200 ease-in"
            leave-from="opacity-100 scale-100"
            leave-to="opacity-0 scale-95"
          >
            <DialogPanel>
              <ab-container :title="title">
                <slot></slot>
              </ab-container>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
