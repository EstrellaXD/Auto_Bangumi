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
const { isMobile } = useBreakpointQuery();

function close() {
  if (props.maskClick) {
    show.value = false;
  }
}
</script>

<template>
  <!-- Mobile: bottom sheet -->
  <ab-bottom-sheet
    v-if="isMobile"
    :show="show"
    :title="title"
    :closeable="maskClick"
    @update:show="show = $event"
  >
    <slot></slot>
  </ab-bottom-sheet>

  <!-- Desktop/Tablet: centered dialog -->
  <TransitionRoot v-else appear :show="show" as="template">
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
  background: rgba(108, 74, 182, 0.15);
  backdrop-filter: blur(4px);
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

:deep(.container-card) {
  border: 1px solid var(--color-primary);
  box-shadow: 0 8px 32px rgba(108, 74, 182, 0.18), 0 2px 8px rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

:deep(.container-header) {
  background: var(--color-primary);
  color: #fff;
  border-bottom: none;
  height: 38px;
}

:deep(.container-body) {
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
</style>
