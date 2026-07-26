<script lang="ts" setup>
import {
  Dialog,
  DialogPanel,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue';
import { storeToRefs } from 'pinia';
import AbSearchPanel from './ab-search-panel.vue';
import { useSearchStore } from '@/store/search';

const searchStore = useSearchStore();
const { showModal } = storeToRefs(searchStore);
const { clearSearch, closeModal } = searchStore;

function dismiss() {
  clearSearch();
  closeModal();
}

function handleSubscribed() {
  closeModal();
}
</script>

<template>
  <TransitionRoot appear :show="showModal" as="template">
    <Dialog :aria-label="$t('mobile.search_title')" @close="dismiss">
      <TransitionChild
        as="template"
        enter="search-modal-backdrop-enter-active"
        enter-from="search-modal-backdrop-enter-from"
        leave="search-modal-backdrop-leave-active"
        leave-to="search-modal-backdrop-leave-to"
      >
        <div class="search-modal-backdrop" aria-hidden="true" />
      </TransitionChild>

      <div class="search-modal">
        <TransitionChild
          as="template"
          enter="search-modal-enter-active"
          enter-from="search-modal-enter-from"
          leave="search-modal-leave-active"
          leave-to="search-modal-leave-to"
        >
          <DialogPanel as="template">
            <div class="search-modal__content">
              <AbSearchPanel
                dismissible
                @dismiss="dismiss"
                @subscribed="handleSubscribed"
              />
            </div>
          </DialogPanel>
        </TransitionChild>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<style lang="scss" scoped>
.search-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-backdrop);
  background: var(--color-overlay);
}

.search-modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 16px 16px;
  overflow-y: auto;

  @include forDesktop {
    padding: 80px 24px 24px;
  }
}

.search-modal__content {
  display: flex;
  width: 100%;
  height: calc(100dvh - 100px);
  max-width: 1100px;
  max-height: calc(100dvh - 100px);
  overflow: hidden;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);

  @supports not (max-height: 1dvh) {
    height: calc(100vh - 100px);
    max-height: calc(100vh - 100px);
  }

  @include forDesktop {
    height: calc(100dvh - 120px);
    max-height: calc(100dvh - 120px);

    @supports not (max-height: 1dvh) {
      height: calc(100vh - 120px);
      max-height: calc(100vh - 120px);
    }
  }
}

.search-modal-enter-active {
  transition: opacity var(--transition-normal),
    transform var(--transition-normal);
}

.search-modal-leave-active {
  transition: opacity 150ms ease-in, transform 150ms ease-in;
}

.search-modal-enter-from,
.search-modal-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}

.search-modal-backdrop-enter-active {
  transition: opacity var(--transition-normal);
}

.search-modal-backdrop-leave-active {
  transition: opacity 150ms ease-in;
}

.search-modal-backdrop-enter-from,
.search-modal-backdrop-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .search-modal-enter-active,
  .search-modal-leave-active,
  .search-modal-backdrop-enter-active,
  .search-modal-backdrop-leave-active {
    transition: none;
  }
}
</style>
