<script lang="ts" setup>
import { Close, Down, Search } from '@icon-park/vue-next';
import { NSpin } from 'naive-ui';
import { onKeyStroke } from '@vueuse/core';
import AbSearchConfirm from './ab-search-confirm.vue';
import type { BangumiRule } from '#/bangumi';
import type { GroupedBangumi } from '@/store/search';

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
  groupedResults,
  showModal,
  selectedResult,
} = storeToRefs(useSearchStore());

const {
  getProviders,
  onSearch,
  clearSearch,
  selectResult,
  clearSelectedResult,
} = useSearchStore();

const subscribing = ref(false);

const showProvider = ref(false);
const searchInputRef = ref<HTMLInputElement | null>(null);

// Tag filter state
const activeFilters = ref<{
  group: string | null;
  resolution: string | null;
  subtitle: string | null;
  season: string | null;
}>({
  group: null,
  resolution: null,
  subtitle: null,
  season: null,
});

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

// Clear filters when search changes
watch(inputValue, () => {
  activeFilters.value = { group: null, resolution: null, subtitle: null, season: null };
});

function onSelectProvider(site: string) {
  provider.value = site;
  showProvider.value = false;
}

function handleVariantSelect(bangumi: BangumiRule) {
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
  activeFilters.value = { group: null, resolution: null, subtitle: null, season: null };
  emit('close');
}

// Get resolution display for variant
function getResolution(bangumi: BangumiRule): string {
  return bangumi.dpi || '';
}

// Get subtitle display for variant
function getSubtitle(bangumi: BangumiRule): string {
  return bangumi.subtitle || '';
}

// Get season display for variant
function getSeason(bangumi: BangumiRule): string {
  if (bangumi.season_raw) return bangumi.season_raw;
  if (bangumi.season) return `S${bangumi.season}`;
  return '';
}

// Resolve poster URL for template
function getPosterUrl(link: string | null | undefined): string {
  return resolvePosterUrl(link);
}

// Toggle filter
function toggleFilter(type: 'group' | 'resolution' | 'subtitle' | 'season', value: string) {
  if (activeFilters.value[type] === value) {
    activeFilters.value[type] = null;
  } else {
    activeFilters.value[type] = value;
  }
}

// Check if variant matches active filters
function variantMatchesFilters(variant: BangumiRule): boolean {
  const { group, resolution, subtitle, season } = activeFilters.value;

  if (group && variant.group_name !== group) return false;
  if (resolution && getResolution(variant) !== resolution) return false;
  if (subtitle && getSubtitle(variant) !== subtitle) return false;
  if (season && getSeason(variant) !== season) return false;

  return true;
}

// Get filtered variants for a group
function getFilteredVariants(group: GroupedBangumi): BangumiRule[] {
  const hasActiveFilter = Object.values(activeFilters.value).some(v => v !== null);
  if (!hasActiveFilter) return group.variants;
  return group.variants.filter(variantMatchesFilters);
}

// Check if tag is active
function isTagActive(type: 'group' | 'resolution' | 'subtitle' | 'season', value: string): boolean {
  return activeFilters.value[type] === value;
}

// Check if any filter is active
const hasActiveFilters = computed(() => Object.values(activeFilters.value).some(v => v !== null));

// Clear all filters
function clearFilters() {
  activeFilters.value = { group: null, resolution: null, subtitle: null, season: null };
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

          <!-- Active Filters Bar -->
          <div v-if="hasActiveFilters" class="active-filters">
            <span class="filter-label">{{ $t('search.filter.active') }}:</span>
            <span v-if="activeFilters.group" class="filter-tag filter-tag-group" @click="toggleFilter('group', activeFilters.group)">
              {{ activeFilters.group }} ×
            </span>
            <span v-if="activeFilters.resolution" class="filter-tag filter-tag-res" @click="toggleFilter('resolution', activeFilters.resolution)">
              {{ activeFilters.resolution }} ×
            </span>
            <span v-if="activeFilters.subtitle" class="filter-tag filter-tag-sub" @click="toggleFilter('subtitle', activeFilters.subtitle)">
              {{ activeFilters.subtitle }} ×
            </span>
            <span v-if="activeFilters.season" class="filter-tag filter-tag-season" @click="toggleFilter('season', activeFilters.season)">
              {{ activeFilters.season }} ×
            </span>
            <button class="clear-filters-btn" @click="clearFilters">{{ $t('search.filter.clear') }}</button>
          </div>

          <!-- Results List -->
          <div class="results-container">
            <!-- Empty state -->
            <div v-if="!loading && groupedResults.length === 0 && inputValue" class="empty-state">
              <p>{{ $t('search.no_results') }}</p>
            </div>

            <!-- Initial state -->
            <div v-else-if="!inputValue && groupedResults.length === 0" class="empty-state">
              <p>{{ $t('search.start_typing') }}</p>
            </div>

            <!-- Bangumi list -->
            <div v-else class="bangumi-list">
              <template v-for="group in groupedResults" :key="group.key">
                <div
                  v-if="getFilteredVariants(group).length > 0"
                  class="bangumi-row"
                >
                  <!-- Left: Poster -->
                  <div class="bangumi-poster">
                    <img
                      v-if="group.poster_link"
                      :src="getPosterUrl(group.poster_link)"
                      :alt="group.official_title"
                    />
                    <div v-else class="bangumi-poster-placeholder">
                      <span class="placeholder-title">{{ group.official_title }}</span>
                    </div>
                  </div>

                  <!-- Right: Variant Grid -->
                  <div class="bangumi-variants">
                    <div
                      v-for="variant in getFilteredVariants(group)"
                      :key="variant.rss_link?.[0] || variant.title_raw"
                      class="variant-chip"
                      @click.stop="handleVariantSelect(variant)"
                    >
                      <span
                        v-if="variant.group_name"
                        class="chip-tag chip-tag-group"
                        :class="{ active: isTagActive('group', variant.group_name) }"
                        @click.stop="toggleFilter('group', variant.group_name)"
                      >{{ variant.group_name }}</span>
                      <span
                        v-if="getResolution(variant)"
                        class="chip-tag chip-tag-res"
                        :class="{ active: isTagActive('resolution', getResolution(variant)) }"
                        @click.stop="toggleFilter('resolution', getResolution(variant))"
                      >{{ getResolution(variant) }}</span>
                      <span
                        v-if="getSubtitle(variant)"
                        class="chip-tag chip-tag-sub"
                        :class="{ active: isTagActive('subtitle', getSubtitle(variant)) }"
                        @click.stop="toggleFilter('subtitle', getSubtitle(variant))"
                      >{{ getSubtitle(variant) }}</span>
                      <span
                        v-if="getSeason(variant)"
                        class="chip-tag chip-tag-season"
                        :class="{ active: isTagActive('season', getSeason(variant)) }"
                        @click.stop="toggleFilter('season', getSeason(variant))"
                      >{{ getSeason(variant) }}</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
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
  max-height: calc(100dvh - 100px); // Use dynamic viewport height for iOS Safari keyboard support
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  transition: background-color var(--transition-normal);

  // Fallback for browsers that don't support dvh
  @supports not (max-height: 1dvh) {
    max-height: calc(100vh - 100px);
  }

  @include forDesktop {
    max-height: calc(100dvh - 120px);

    @supports not (max-height: 1dvh) {
      max-height: calc(100vh - 120px);
    }
  }
}

// Header
.modal-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  transition: border-color var(--transition-normal);

  @include forTablet {
    gap: 12px;
    padding: 16px;
  }
}

.search-input-wrapper {
  flex: 1;
  min-width: 0; // Allow shrinking
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding-left: 12px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), background-color var(--transition-normal);

  @include forTablet {
    gap: 10px;
    height: 44px;
    padding-left: 14px;
  }

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
  gap: 4px;
  height: 100%;
  padding: 0 10px;
  min-width: 70px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
  transition: background-color var(--transition-fast);

  @include forTablet {
    gap: 6px;
    padding: 0 14px;
    min-width: 90px;
    font-size: 13px;
  }

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
  width: 36px;
  height: 36px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-muted);
  flex-shrink: 0;
  transition: all var(--transition-fast);

  @include forTablet {
    width: 44px;
    height: 44px;
  }

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

// Bangumi list
.bangumi-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bangumi-row {
  display: flex;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.bangumi-poster {
  width: 100px;
  flex-shrink: 0;

  @include forDesktop {
    width: 120px;
  }

  img {
    width: 100%;
    aspect-ratio: 5 / 7;
    object-fit: cover;
    border-radius: var(--radius-md);
    background: var(--color-surface-hover);
  }
}

.bangumi-poster-placeholder {
  width: 100%;
  aspect-ratio: 5 / 7;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border-radius: var(--radius-md);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
}

.placeholder-title {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-muted);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  line-height: 1.3;
}

.bangumi-variants {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}

.variant-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    background: var(--color-primary);

    .chip-tag {
      background: rgba(255, 255, 255, 0.2);
      color: #fff;
    }
  }
}

.chip-tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.chip-tag-group {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.chip-tag-res {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);
}

.chip-tag-sub {
  background: rgba(249, 115, 22, 0.15);
  color: var(--color-accent);
}

.chip-tag-season {
  background: rgba(139, 92, 246, 0.15);
  color: rgb(139, 92, 246);
}

// Active filters bar
.active-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--color-surface-hover);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.filter-tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition-fast);

  &:hover {
    opacity: 0.8;
  }
}

.filter-tag-group {
  background: var(--color-primary);
  color: #fff;
}

.filter-tag-res {
  background: var(--color-success);
  color: #fff;
}

.filter-tag-sub {
  background: var(--color-accent);
  color: #fff;
}

.filter-tag-season {
  background: rgb(139, 92, 246);
  color: #fff;
}

.clear-filters-btn {
  margin-left: auto;
  padding: 4px 10px;
  font-size: 12px;
  font-family: inherit;
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-danger);
    color: var(--color-danger);
  }
}

// Active tag highlight
.chip-tag.active {
  box-shadow: 0 0 0 2px var(--color-primary);
}
</style>
