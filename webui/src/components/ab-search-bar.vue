<script lang="ts" setup>
import {
  Popover,
  PopoverButton,
  PopoverOverlay,
  PopoverPanel,
} from '@headlessui/vue';
import { vOnClickOutside } from '@vueuse/components';
import { Search } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

defineEmits<{
  (e: 'add-bangumi', bangumiRule: BangumiRule): void;
}>();

const { providers, provider, loading, inputValue, bangumiList } = storeToRefs(
  useSearchStore()
);
const { getProviders, onSearch, clearSearch } = useSearchStore();

onMounted(() => {
  getProviders();
});
</script>

<template>
  <Popover v-bind="$attrs">
    <transition name="fade">
      <PopoverOverlay
        class="fixed top-0 left-0 w-full h-full bg-black bg-opacity-50 z-5"
      />
    </transition>

    <PopoverButton bg-transparent text="pc:24 20" is-btn btn-click>
      <Search size="1em" fill="#fff" />
    </PopoverButton>

    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="translate-y--20 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y--20 opacity-0"
    >
      <PopoverPanel
        v-on-click-outside="clearSearch"
        class="search-panel"
        fixed
        left-0
        right-0
        m-auto
        w-max
        z-5
      >
        <ab-search
          v-model:inputValue="inputValue"
          v-model:provider="provider"
          :providers="providers"
          :loading="loading"
          @search="onSearch"
        />

        <div class="search-list" space-y-10 overflow-auto>
          <transition-group name="fade-list">
            <template v-for="bangumi in bangumiList" :key="bangumi.order">
              <ab-bangumi-card
                :bangumi="bangumi.value"
                type="search"
                @click="() => $emit('add-bangumi', bangumi.value)"
              />
            </template>
          </transition-group>
        </div>
      </PopoverPanel>
    </transition>
  </Popover>
</template>

<style lang="scss" scoped>
.search-panel {
  --_offset-top: 80px;
  --_offset-bottom: 40px;
  --_search-input-height: 36px;
  --_search-list-offset: 20px;

  @include forMobile {
    --_offset-top: 65px;
    --_search-list-offset: 10px;
  }

  top: var(--_offset-top);

  .search-list {
    margin-top: var(--_search-list-offset);
    max-height: calc(
      100vh - var(--_offset-top) - var(--_offset-bottom) -
        var(--_search-input-height) - var(--_search-list-offset)
    );
  }
}
</style>
