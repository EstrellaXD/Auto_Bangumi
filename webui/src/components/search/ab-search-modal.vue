<script lang="ts" setup>
import { Close, Down, Search } from '@icon-park/vue-next';
import { NSpin } from 'naive-ui';
import { onKeyStroke } from '@vueuse/core';
import AbSearchFilters from './ab-search-filters.vue';
import AbSearchCard from './ab-search-card.vue';
import AbSearchConfirm from './ab-search-confirm.vue';
import type { BangumiRule } from '#/bangumi';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const message = useMessage();
const { getAll } = useBangumiStore();

const {
  providers,
  provider,
  loading,
  inputValue,
  bangumiList,
  filteredResults,
  filters,
  filterOptions,
  showModal,
  selectedResult,
} = storeToRefs(useSearchStore());

const {
  getProviders,
  onSearch,
  clearSearch,
  toggleFilter,
  clearFilters,
  selectResult,
  clearSelectedResult,
} = useSearchStore();

const subscribing = ref(false);

const showProvider = ref(false);
const searchInputRef = ref<HTMLInputElement | null>(null);

// Close on Escape
onKeyStroke('Escape', () => {
  if (selectedResult.value) {
    clearSelectedResult();
  } else {
    emit('close');
  }
});

// Focus input on mount
onMounted(() => {
  getProviders();
  nextTick(() => {
    searchInputRef.value?.focus();
  });
});

function onSelectProvider(site: string) {
  provider.value = site;
  showProvider.value = false;
}

function handleCardClick(bangumi: BangumiRule) {
  selectResult(bangumi);
}

async function handleConfirm(bangumi: BangumiRule) {
  subscribing.value = true;
  try {
    // Create RSS object from bangumi data
    const rss = {
      id: 0,
      name: bangumi.official_title,
      url: bangumi.rss_link?.[0] || '',
      aggregate: false,
      parser: 'mikan',
      enabled: true,
      connection_status: null,
      last_checked_at: null,
      last_error: null,
    };
    await apiDownload.subscribe(bangumi, rss);
    message.success('订阅成功');
    getAll();
    clearSelectedResult();
    emit('close');
  } catch (e) {
    console.error('Subscribe failed:', e);
    message.error('订阅失败');
  } finally {
    subscribing.value = false;
  }
}

function handleClose() {
  clearSearch();
  emit('close');
}
</script>

<template>
  <Teleport to="body">
    <!-- Backdrop -->
    <transition name="overlay">
      <div v-if="showModal" class="modal-backdrop" />
    </transition>

    <!-- Modal -->
    <transition name="modal">
      <div v-if="showModal" class="modal-container" role="dialog" aria-modal="true">
        <div class="modal-content">
          <!-- Header -->
          <header class="modal-header">
            <div class="search-input-wrapper">
              <button
                v-if="!loading"
                class="search-icon-btn"
                aria-label="Search"
                @click="onSearch"
              >
                <Search theme="outline" size="20" />
              </button>
              <NSpin v-else :size="18" />

              <input
                ref="searchInputRef"
                v-model="inputValue"
                type="text"
                :placeholder="$t('topbar.search.placeholder')"
                class="search-input"
                aria-label="Search anime"
                @keyup.enter="onSearch"
              />

              <div class="provider-select">
                <button
                  class="provider-btn"
                  aria-label="Select search provider"
                  @click="showProvider = !showProvider"
                >
                  <span class="provider-label">{{ provider }}</span>
                  <Down :size="14" />
                </button>

                <transition name="dropdown">
                  <div v-show="showProvider" class="provider-dropdown">
                    <button
                      v-for="site in providers"
                      :key="site"
                      class="provider-item"
                      :class="{ active: site === provider }"
                      @click="onSelectProvider(site)"
                    >
                      {{ site }}
                    </button>
                  </div>
                </transition>
              </div>
            </div>

            <button class="close-btn" aria-label="Close search" @click="handleClose">
              <Close theme="outline" size="20" />
            </button>
          </header>

          <!-- Filters -->
          <AbSearchFilters
            :filters="filters"
            :filter-options="filterOptions"
            :filtered-count="filteredResults.length"
            :total-count="bangumiList.length"
            @toggle-filter="toggleFilter"
            @clear-filters="clearFilters"
          />

          <!-- Results Grid -->
          <div class="results-container">
            <!-- Empty state -->
            <div v-if="!loading && filteredResults.length === 0 && inputValue" class="empty-state">
              <p>{{ $t('search.no_results') }}</p>
            </div>

            <!-- Initial state -->
            <div v-else-if="!inputValue && filteredResults.length === 0" class="empty-state">
              <p>{{ $t('search.start_typing') }}</p>
            </div>

            <!-- Results grid -->
            <transition-group
              v-else
              name="card"
              tag="div"
              class="results-grid"
            >
              <AbSearchCard
                v-for="(result, index) in filteredResults"
                :key="result.order"
                :bangumi="result.value"
                :style="{ '--stagger-index': index }"
                @select="handleCardClick"
              />
            </transition-group>
          </div>
        </div>

        <!-- Confirmation Modal -->
        <AbSearchConfirm
          v-if="selectedResult"
          :bangumi="selectedResult"
          @confirm="handleConfirm"
          @cancel="clearSelectedResult"
        />
      </div>
    </transition>
  </Teleport>
</template>

<style lang="scss" scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-overlay);
  z-index: var(--z-modal-backdrop);
}

.modal-container {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 16px 16px;
  z-index: var(--z-modal);
  overflow-y: auto;

  @include forDesktop {
    padding: 80px 24px 24px;
  }
}

.modal-content {
  width: 100%;
  max-width: 1100px;
  max-height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  transition: background-color var(--transition-normal);

  @include forDesktop {
    max-height: calc(100vh - 120px);
  }
}

// Header
.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  transition: border-color var(--transition-normal);
}

.search-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding-left: 14px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), background-color var(--transition-normal);

  &:focus-within {
    border-color: var(--color-primary);
    background: var(--color-surface);
  }
}

.search-icon-btn {
  display: flex;
  align-items: center;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: color var(--transition-fast);

  &:hover {
    color: var(--color-primary);
  }
}

.search-input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  font-size: 15px;
  color: var(--color-text);

  &::placeholder {
    color: var(--color-text-muted);
  }
}

.provider-select {
  position: relative;
  height: 100%;
}

.provider-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 100%;
  padding: 0 14px;
  min-width: 90px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }
}

.provider-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.provider-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 120px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 10;
}

.provider-item {
  display: block;
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  color: var(--color-text);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background-color var(--transition-fast), color var(--transition-fast);

  &:hover {
    background: var(--color-primary);
    color: #fff;
  }

  &.active {
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-muted);
  flex-shrink: 0;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-danger);
    border-color: var(--color-danger);
    color: #fff;
  }
}

// Results
.results-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.results-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr;

  @include forTablet {
    grid-template-columns: repeat(2, 1fr);
  }

  @include forDesktop {
    grid-template-columns: repeat(3, 1fr);
  }

  @media screen and (min-width: 1200px) {
    grid-template-columns: repeat(4, 1fr);
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-muted);
  font-size: 15px;
}

// Modal transition
.modal-enter-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}

.modal-leave-active {
  transition: opacity 150ms ease-in, transform 150ms ease-in;
}

.modal-enter-from {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}

.modal-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-10px);
}

// Card stagger animation
.card-enter-active {
  transition: opacity var(--transition-slow), transform var(--transition-slow);
  transition-delay: calc(var(--stagger-index, 0) * 40ms);
}

.card-leave-active {
  transition: opacity 150ms ease-in;
}

.card-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.card-leave-to {
  opacity: 0;
}
</style>
