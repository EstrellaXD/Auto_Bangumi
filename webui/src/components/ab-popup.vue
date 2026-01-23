<script lang="ts" setup>
import {
  Dialog,
  DialogPanel,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue';

const props = withDefaults(
  defineProps<{
    title: string;
    maskClick?: boolean;
    css?: string;
  }>(),
  {
    title: 'title',
    maskClick: true,
    css: '',
  }
);

const show = defineModel('show', { default: false });

function close() {
  if (props.maskClick) {
    show.value = false;
  }
}
</script>

<template>
  <TransitionRoot appear :show="show" as="template">
    <Dialog as="div" class="popup-dialog" @close="close">
      <TransitionChild
        as="template"
        enter="duration-300 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-200 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="popup-backdrop" />
      </TransitionChild>

      <div class="popup-wrapper">
        <div class="popup-center">
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
              <ab-container :title="title" :class="[css]">
                <slot></slot>
              </ab-container>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<style lang="scss" scoped>
.popup-dialog {
  position: relative;
  z-index: 40;
}

.popup-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
}

.popup-wrapper {
  position: fixed;
  inset: 0;
  overflow-y: auto;
}

.popup-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 16px;
  text-align: center;
}
</style>
