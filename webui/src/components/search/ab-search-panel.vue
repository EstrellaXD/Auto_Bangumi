<script lang="ts" setup>
import {
  Calendar,
  Close,
  Down,
  Monitor,
  PeoplesTwo,
  Search,
  Translate,
} from '@icon-park/vue-next';
import { NSpin } from 'naive-ui';
import { useId } from 'vue';
import { onClickOutside, onKeyStroke } from '@vueuse/core';
import AbSearchConfirm from './ab-search-confirm.vue';
import type { BangumiRule } from '#/bangumi';
import type { GroupedBangumi } from '@/store/search';

const props = withDefaults(
  defineProps<{
    dismissible?: boolean;
  }>(),
  {
    dismissible: false,
  }
);

const emit = defineEmits<{
  (e: 'dismiss'): void;
  (e: 'subscribed'): void;
}>();

const message = useMessage();
const { t } = useMyI18n();
const { getAll } = useBangumiStore();

const {
  providers,
  provider,
  loading,
  searchFailed,
  inputValue,
  groupedResults,
  selectedResult,
  activeFilters,
} = storeToRefs(useSearchStore());

const {
  getProviders,
  onSearch,
  closeSearch,
  selectResult,
  clearSelectedResult,
  clearFilters,
} = useSearchStore();

const subscribing = ref(false);
const panelActive = ref(true);

const showProvider = ref(false);
const searchInputRef = ref<HTMLInputElement | null>(null);
const providerSelectRef = ref<HTMLElement | null>(null);
const providerButtonRef = ref<HTMLButtonElement | null>(null);
const providerOptionsId = useId();

// Max visible chips per category
const MAX_VISIBLE_CHIPS = 6;

// Max visible variants per bangumi (fits ~4 rows, ~3 items per row)
const MAX_VISIBLE_VARIANTS = 12;

// Track which categories are expanded
const expandedCategories = ref<
  Set<'group' | 'resolution' | 'subtitle' | 'season'>
>(new Set());

// Track which bangumi groups have expanded variants
const expandedVariants = ref<Set<string>>(new Set());

// Close EventSource on unmount (prevents leak if navigating away mid-search)
onBeforeUnmount(() => {
  closeSearch();
});

onActivated(() => {
  panelActive.value = true;
});

onDeactivated(() => {
  panelActive.value = false;
  closeProvider(false);
});

onClickOutside(providerSelectRef, () => closeProvider(false));

onKeyStroke('Escape', () => {
  if (!panelActive.value) return;
  if (selectedResult.value) {
    clearSelectedResult();
    return;
  }
  if (showProvider.value) {
    closeProvider(true);
    return;
  }
  if (props.dismissible) emit('dismiss');
});

function focusInput() {
  nextTick(() => {
    searchInputRef.value?.focus();
  });
}

defineExpose({ focusInput });

onMounted(() => {
  getProviders();
  focusInput();
});

// Clear filters when search changes
watch(inputValue, () => {
  expandedCategories.value.clear();
  expandedVariants.value.clear();
});

function onSelectProvider(site: string) {
  provider.value = site;
  closeProvider(true);
}

function closeProvider(restoreFocus: boolean) {
  if (!showProvider.value) return;
  showProvider.value = false;
  if (restoreFocus) {
    nextTick(() => providerButtonRef.value?.focus());
  }
}

function toggleProvider() {
  if (showProvider.value) {
    closeProvider(false);
  } else {
    showProvider.value = true;
  }
}

function handleProviderEscape(event: KeyboardEvent) {
  if (!showProvider.value) return;
  event.stopPropagation();
  closeProvider(true);
}

function handleVariantSelect(bangumi: BangumiRule) {
  closeProvider(false);
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
      parser: provider.value,
      enabled: true,
      connection_status: null,
      last_checked_at: null,
      last_error: null,
    };
    await apiDownload.subscribe(bangumi, rss);
    message.success(t('search.subscribe_success'));
    getAll();
    clearSelectedResult();
    emit('subscribed');
  } catch (e) {
    console.error('Subscribe failed:', e);
    message.error(t('search.subscribe_failed'));
  } finally {
    subscribing.value = false;
  }
}

// Normalize resolution to standard format
function normalizeResolution(raw: string): string {
  if (!raw) return '';
  const lower = raw.toLowerCase();

  // 4K variants
  if (lower.includes('4k') || lower.includes('2160') || lower.includes('uhd')) {
    return '4K';
  }
  // 1080p variants
  if (
    lower.includes('1080') ||
    lower.includes('fhd') ||
    lower.includes('1920')
  ) {
    return 'FHD';
  }
  // 720p variants
  if (lower.includes('720') || lower === 'hd') {
    return 'HD';
  }
  // 480p/SD
  if (lower.includes('480') || lower === 'sd') {
    return 'SD';
  }

  return raw; // Return original if no match
}

// Normalize subtitle to standard format
function normalizeSubtitle(raw: string): string {
  if (!raw) return '';
  const lower = raw.toLowerCase();

  // Check for dual/bilingual first
  if (
    lower.includes('双语') ||
    lower.includes('dual') ||
    (lower.includes('简') && lower.includes('繁')) ||
    (lower.includes('chs') && lower.includes('cht'))
  ) {
    return '双语';
  }

  // Simplified Chinese
  if (lower.includes('简') || lower.includes('chs') || lower === 'sc') {
    if (lower.includes('内嵌') || lower.includes('内封')) {
      return '简/内嵌';
    }
    return '简';
  }

  // Traditional Chinese
  if (lower.includes('繁') || lower.includes('cht') || lower === 'tc') {
    if (lower.includes('内嵌') || lower.includes('内封')) {
      return '繁/内嵌';
    }
    return '繁';
  }

  // Japanese
  if (lower.includes('日') || lower.includes('jp') || lower.includes('ja')) {
    return '日';
  }

  // Embedded/Internal subs
  if (lower.includes('内嵌') || lower.includes('内封')) {
    return '内嵌';
  }

  // External subs
  if (
    lower.includes('外挂') ||
    lower.includes('ass') ||
    lower.includes('srt')
  ) {
    return '外挂';
  }

  return raw; // Return original if no match
}

// Normalize season to standard format
function normalizeSeason(raw: string): string {
  if (!raw) return '';

  // Already in S1/S2 format
  if (/^S\d+$/i.test(raw)) {
    return raw.toUpperCase();
  }

  // Extract season number
  const match = raw.match(/(\d+)/);
  if (match) {
    return `S${match[1]}`;
  }

  // Special types
  const lower = raw.toLowerCase();
  if (
    lower.includes('剧场') ||
    lower.includes('movie') ||
    lower.includes('劇場')
  ) {
    return '剧场版';
  }
  if (lower.includes('ova')) {
    return 'OVA';
  }
  if (lower.includes('sp') || lower.includes('special')) {
    return 'SP';
  }

  return raw;
}

// Get resolution display for variant (normalized)
function getResolution(bangumi: BangumiRule): string {
  return normalizeResolution(bangumi.dpi || '');
}

// Get subtitle display for variant (normalized)
function getSubtitle(bangumi: BangumiRule): string {
  return normalizeSubtitle(bangumi.subtitle || '');
}

// Get season display for variant (normalized)
function getSeason(bangumi: BangumiRule): string {
  if (bangumi.season_raw) return normalizeSeason(bangumi.season_raw);
  if (bangumi.season) return `S${bangumi.season}`;
  return '';
}

// Resolve poster URL for template
function getPosterUrl(link: string | null | undefined): string {
  return resolvePosterUrl(link);
}

// Extract all filter options from grouped results
const filterOptions = computed(() => {
  const groups = new Set<string>();
  const resolutions = new Set<string>();
  const subtitles = new Set<string>();
  const seasons = new Set<string>();

  for (const group of groupedResults.value) {
    for (const variant of group.variants) {
      if (variant.group_name) groups.add(variant.group_name);
      const res = getResolution(variant);
      if (res) resolutions.add(res);
      const sub = getSubtitle(variant);
      if (sub) subtitles.add(sub);
      const season = getSeason(variant);
      if (season) seasons.add(season);
    }
  }

  return {
    group: Array.from(groups).sort(),
    resolution: Array.from(resolutions).sort((a, b) => {
      const order = ['4K', 'FHD', 'HD', 'SD'];
      const aIndex = order.indexOf(a);
      const bIndex = order.indexOf(b);
      // Put unknown resolutions at the end
      if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    }),
    subtitle: Array.from(subtitles).sort((a, b) => {
      const order = [
        '简',
        '繁',
        '双语',
        '简/内嵌',
        '繁/内嵌',
        '内嵌',
        '外挂',
        '日',
      ];
      const aIndex = order.indexOf(a);
      const bIndex = order.indexOf(b);
      if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
      if (aIndex === -1) return 1;
      if (bIndex === -1) return -1;
      return aIndex - bIndex;
    }),
    season: Array.from(seasons).sort((a, b) => {
      // Sort S1, S2, S3... then special types
      const aMatch = a.match(/^S(\d+)$/);
      const bMatch = b.match(/^S(\d+)$/);
      if (aMatch && bMatch) {
        return parseInt(aMatch[1]) - parseInt(bMatch[1]);
      }
      if (aMatch) return -1;
      if (bMatch) return 1;
      return a.localeCompare(b);
    }),
  };
});

// Check if filter section should be visible
const showFilters = computed(() => {
  return (
    groupedResults.value.length > 0 &&
    (filterOptions.value.group.length > 0 ||
      filterOptions.value.resolution.length > 0 ||
      filterOptions.value.subtitle.length > 0 ||
      filterOptions.value.season.length > 0)
  );
});

// Toggle filter (multi-select)
function toggleFilter(
  type: 'group' | 'resolution' | 'subtitle' | 'season',
  value: string
) {
  const index = activeFilters.value[type].indexOf(value);
  if (index === -1) {
    activeFilters.value[type].push(value);
  } else {
    activeFilters.value[type].splice(index, 1);
  }
}

// Check if filter chip is active
function isFilterActive(
  type: 'group' | 'resolution' | 'subtitle' | 'season',
  value: string
): boolean {
  return activeFilters.value[type].includes(value);
}

// Check if variant matches active filters
function variantMatchesFilters(variant: BangumiRule): boolean {
  const { group, resolution, subtitle, season } = activeFilters.value;

  if (
    group.length > 0 &&
    (!variant.group_name || !group.includes(variant.group_name))
  ) {
    return false;
  }
  if (resolution.length > 0) {
    const res = getResolution(variant);
    if (!res || !resolution.includes(res)) return false;
  }
  if (subtitle.length > 0) {
    const sub = getSubtitle(variant);
    if (!sub || !subtitle.includes(sub)) return false;
  }
  if (season.length > 0) {
    const s = getSeason(variant);
    if (!s || !season.includes(s)) return false;
  }

  return true;
}

// Get filtered variants for a group
function getFilteredVariants(group: GroupedBangumi): BangumiRule[] {
  const hasActiveFilter = Object.values(activeFilters.value).some(
    (arr) => arr.length > 0
  );
  if (!hasActiveFilter) return group.variants;
  return group.variants.filter(variantMatchesFilters);
}

// Check if any filter is active
const hasActiveFilters = computed(() =>
  Object.values(activeFilters.value).some((arr) => arr.length > 0)
);

// Get all selected filter tags for display
const selectedFilterTags = computed(() => {
  const tags: {
    type: 'group' | 'resolution' | 'subtitle' | 'season';
    value: string;
  }[] = [];
  for (const value of activeFilters.value.group) {
    tags.push({ type: 'group', value });
  }
  for (const value of activeFilters.value.resolution) {
    tags.push({ type: 'resolution', value });
  }
  for (const value of activeFilters.value.subtitle) {
    tags.push({ type: 'subtitle', value });
  }
  for (const value of activeFilters.value.season) {
    tags.push({ type: 'season', value });
  }
  return tags;
});

// Count total and filtered results
const totalVariantCount = computed(() => {
  return groupedResults.value.reduce(
    (sum, group) => sum + group.variants.length,
    0
  );
});

const filteredVariantCount = computed(() => {
  if (!hasActiveFilters.value) return totalVariantCount.value;
  return groupedResults.value.reduce(
    (sum, group) => sum + getFilteredVariants(group).length,
    0
  );
});

// Get visible options (limited or all if expanded)
function getVisibleOptions(
  category: 'group' | 'resolution' | 'subtitle' | 'season',
  options: string[]
) {
  if (expandedCategories.value.has(category)) {
    return options;
  }
  return options.slice(0, MAX_VISIBLE_CHIPS);
}

function getOverflowCount(options: string[]) {
  return Math.max(0, options.length - MAX_VISIBLE_CHIPS);
}

function hasOverflow(options: string[]) {
  return options.length > MAX_VISIBLE_CHIPS;
}

function isExpanded(category: 'group' | 'resolution' | 'subtitle' | 'season') {
  return expandedCategories.value.has(category);
}

function toggleExpand(
  category: 'group' | 'resolution' | 'subtitle' | 'season'
) {
  if (expandedCategories.value.has(category)) {
    expandedCategories.value.delete(category);
  } else {
    expandedCategories.value.add(category);
  }
}

// Variant expansion functions
function getVisibleVariants(group: GroupedBangumi): BangumiRule[] {
  const filtered = getFilteredVariants(group);
  if (expandedVariants.value.has(group.key)) {
    return filtered;
  }
  return filtered.slice(0, MAX_VISIBLE_VARIANTS);
}

function getVariantOverflowCount(group: GroupedBangumi): number {
  const filtered = getFilteredVariants(group);
  return Math.max(0, filtered.length - MAX_VISIBLE_VARIANTS);
}

function hasVariantOverflow(group: GroupedBangumi): boolean {
  return getFilteredVariants(group).length > MAX_VISIBLE_VARIANTS;
}

function isVariantsExpanded(groupKey: string): boolean {
  return expandedVariants.value.has(groupKey);
}

function toggleVariantsExpand(groupKey: string) {
  if (expandedVariants.value.has(groupKey)) {
    expandedVariants.value.delete(groupKey);
  } else {
    expandedVariants.value.add(groupKey);
  }
}

// Get all variants as a flat list
const allVariants = computed(() => {
  const variants: BangumiRule[] = [];
  for (const group of groupedResults.value) {
    variants.push(...group.variants);
  }
  return variants;
});

// Check if adding a filter value would produce any results
// This checks if the value is compatible with current selections in OTHER categories
function wouldProduceResults(
  type: 'group' | 'resolution' | 'subtitle' | 'season',
  value: string
): boolean {
  const { group, resolution, subtitle, season } = activeFilters.value;

  // If this filter is already active, it's selectable (to allow deselection)
  if (activeFilters.value[type].includes(value)) {
    return true;
  }

  // Check if any variant matches the hypothetical filter combination
  return allVariants.value.some((variant) => {
    // Check group constraint
    const groupMatch =
      type === 'group'
        ? variant.group_name === value
        : group.length === 0 ||
          (variant.group_name && group.includes(variant.group_name));

    if (!groupMatch) return false;

    // Check resolution constraint
    const res = getResolution(variant);
    const resMatch =
      type === 'resolution'
        ? res === value
        : resolution.length === 0 || (res && resolution.includes(res));

    if (!resMatch) return false;

    // Check subtitle constraint
    const sub = getSubtitle(variant);
    const subMatch =
      type === 'subtitle'
        ? sub === value
        : subtitle.length === 0 || (sub && subtitle.includes(sub));

    if (!subMatch) return false;

    // Check season constraint
    const s = getSeason(variant);
    const seasonMatch =
      type === 'season'
        ? s === value
        : season.length === 0 || (s && season.includes(s));

    if (!seasonMatch) return false;

    return true;
  });
}

// Check if a filter option is disabled (would produce no results)
function isFilterDisabled(
  type: 'group' | 'resolution' | 'subtitle' | 'season',
  value: string
): boolean {
  // Only disable when there are active filters
  if (!hasActiveFilters.value) return false;
  return !wouldProduceResults(type, value);
}

// Handle filter click - only toggle if not disabled
function handleFilterClick(
  type: 'group' | 'resolution' | 'subtitle' | 'season',
  value: string
) {
  if (isFilterDisabled(type, value)) return;
  toggleFilter(type, value);
}
</script>

<template>
  <div class="search-panel">
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
          :aria-label="$t('mobile.search_title')"
          @keyup.enter="onSearch"
        />

        <div
          ref="providerSelectRef"
          class="provider-select"
          @keydown.esc="handleProviderEscape"
        >
          <button
            ref="providerButtonRef"
            class="provider-btn"
            aria-label="Select search provider"
            :aria-controls="providerOptionsId"
            :aria-expanded="showProvider"
            @click="toggleProvider"
          >
            <span class="provider-label">{{ provider }}</span>
            <Down :size="14" />
          </button>

          <transition name="dropdown">
            <div
              v-if="showProvider"
              :id="providerOptionsId"
              class="provider-dropdown"
            >
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

      <ab-icon-button
        v-if="dismissible"
        class="modal-close-btn"
        :label="$t('common.close')"
        @click="emit('dismiss')"
      >
        <Close theme="outline" size="20" />
      </ab-icon-button>
    </header>

    <!-- Filter Section - Chip Cloud -->
    <section v-if="showFilters" class="filter-section">
      <!-- Group Filters -->
      <div v-if="filterOptions.group.length > 0" class="filter-category">
        <span class="category-icon">
          <PeoplesTwo theme="outline" :size="16" />
        </span>
        <div class="filter-chips">
          <button
            v-for="option in getVisibleOptions('group', filterOptions.group)"
            :key="option"
            class="filter-chip chip-group"
            :class="{
              active: isFilterActive('group', option),
              disabled: isFilterDisabled('group', option),
            }"
            :disabled="isFilterDisabled('group', option)"
            @click="handleFilterClick('group', option)"
          >
            {{ option }}
          </button>
          <button
            v-if="hasOverflow(filterOptions.group)"
            class="expand-btn"
            @click="toggleExpand('group')"
          >
            {{
              isExpanded('group')
                ? $t('search.filter.collapse')
                : `+${getOverflowCount(filterOptions.group)}`
            }}
          </button>
        </div>
      </div>

      <!-- Resolution Filters -->
      <div v-if="filterOptions.resolution.length > 0" class="filter-category">
        <span class="category-icon">
          <Monitor theme="outline" :size="16" />
        </span>
        <div class="filter-chips">
          <button
            v-for="option in getVisibleOptions(
              'resolution',
              filterOptions.resolution
            )"
            :key="option"
            class="filter-chip chip-resolution"
            :class="{
              active: isFilterActive('resolution', option),
              disabled: isFilterDisabled('resolution', option),
            }"
            :disabled="isFilterDisabled('resolution', option)"
            @click="handleFilterClick('resolution', option)"
          >
            {{ option }}
          </button>
          <button
            v-if="hasOverflow(filterOptions.resolution)"
            class="expand-btn"
            @click="toggleExpand('resolution')"
          >
            {{
              isExpanded('resolution')
                ? $t('search.filter.collapse')
                : `+${getOverflowCount(filterOptions.resolution)}`
            }}
          </button>
        </div>
      </div>

      <!-- Subtitle Filters -->
      <div v-if="filterOptions.subtitle.length > 0" class="filter-category">
        <span class="category-icon">
          <Translate theme="outline" :size="16" />
        </span>
        <div class="filter-chips">
          <button
            v-for="option in getVisibleOptions(
              'subtitle',
              filterOptions.subtitle
            )"
            :key="option"
            class="filter-chip chip-subtitle"
            :class="{
              active: isFilterActive('subtitle', option),
              disabled: isFilterDisabled('subtitle', option),
            }"
            :disabled="isFilterDisabled('subtitle', option)"
            @click="handleFilterClick('subtitle', option)"
          >
            {{ option }}
          </button>
          <button
            v-if="hasOverflow(filterOptions.subtitle)"
            class="expand-btn"
            @click="toggleExpand('subtitle')"
          >
            {{
              isExpanded('subtitle')
                ? $t('search.filter.collapse')
                : `+${getOverflowCount(filterOptions.subtitle)}`
            }}
          </button>
        </div>
      </div>

      <!-- Season Filters -->
      <div v-if="filterOptions.season.length > 0" class="filter-category">
        <span class="category-icon">
          <Calendar theme="outline" :size="16" />
        </span>
        <div class="filter-chips">
          <button
            v-for="option in getVisibleOptions('season', filterOptions.season)"
            :key="option"
            class="filter-chip chip-season"
            :class="{
              active: isFilterActive('season', option),
              disabled: isFilterDisabled('season', option),
            }"
            :disabled="isFilterDisabled('season', option)"
            @click="handleFilterClick('season', option)"
          >
            {{ option }}
          </button>
          <button
            v-if="hasOverflow(filterOptions.season)"
            class="expand-btn"
            @click="toggleExpand('season')"
          >
            {{
              isExpanded('season')
                ? $t('search.filter.collapse')
                : `+${getOverflowCount(filterOptions.season)}`
            }}
          </button>
        </div>
      </div>

      <!-- Selected Filters Summary -->
      <div class="filter-summary">
        <div v-if="hasActiveFilters" class="selected-filters">
          <span class="selected-label">{{ $t('search.filter.active') }}:</span>
          <div class="selected-chips">
            <button
              v-for="tag in selectedFilterTags"
              :key="`${tag.type}-${tag.value}`"
              class="selected-chip"
              :class="`chip-${tag.type}`"
              :aria-label="`${$t('search.filter.clear')} ${tag.value}`"
              @click="toggleFilter(tag.type, tag.value)"
            >
              {{ tag.value }} &times;
            </button>
          </div>
          <button class="clear-all-btn" @click="clearFilters">
            {{ $t('search.filter.clear') }}
          </button>
        </div>
        <span class="results-count">
          <template v-if="hasActiveFilters">
            {{ filteredVariantCount }} / {{ totalVariantCount }}
            {{ $t('search.filter.results') }}
          </template>
          <template v-else>
            {{ totalVariantCount }} {{ $t('search.filter.results') }}
          </template>
        </span>
      </div>
    </section>

    <!-- Results List -->
    <div class="results-container">
      <!-- Failure state (connection/server error, distinct from zero matches) -->
      <div v-if="!loading && searchFailed" class="empty-state">
        <p>{{ $t('search.failed_hint') }}</p>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!loading && groupedResults.length === 0 && inputValue"
        class="empty-state"
      >
        <p>{{ $t('search.no_results') }}</p>
      </div>

      <!-- Initial state -->
      <div
        v-else-if="!inputValue && groupedResults.length === 0"
        class="empty-state"
      >
        <p>{{ $t('search.start_typing') }}</p>
      </div>

      <!-- Bangumi list -->
      <div v-else class="bangumi-list">
        <template v-for="group in groupedResults" :key="group.key">
          <div v-if="getFilteredVariants(group).length > 0" class="bangumi-row">
            <!-- Left: Poster -->
            <div class="bangumi-poster">
              <img
                v-if="group.poster_link"
                :src="getPosterUrl(group.poster_link)"
                :alt="group.official_title"
              />
              <div v-else class="bangumi-poster-placeholder">
                <span class="placeholder-title">{{
                  group.official_title
                }}</span>
              </div>
            </div>

            <!-- Right: Variant Chips (Original Prototype 4) -->
            <div class="bangumi-variants">
              <button
                v-for="variant in getVisibleVariants(group)"
                :key="variant.rss_link?.[0] || variant.title_raw"
                class="variant-chip"
                type="button"
                @click="handleVariantSelect(variant)"
              >
                <span class="tag tag-group">{{
                  variant.group_name || 'Unknown'
                }}</span>
                <span v-if="getResolution(variant)" class="tag tag-res">
                  {{ getResolution(variant) }}
                </span>
                <span v-if="getSubtitle(variant)" class="tag tag-sub">
                  {{ getSubtitle(variant) }}
                </span>
                <span v-if="getSeason(variant)" class="tag tag-season">
                  {{ getSeason(variant) }}
                </span>
              </button>
              <button
                v-if="hasVariantOverflow(group)"
                class="variant-expand-btn"
                @click="toggleVariantsExpand(group.key)"
              >
                {{
                  isVariantsExpanded(group.key)
                    ? $t('search.filter.collapse')
                    : `+${getVariantOverflowCount(group)}`
                }}
              </button>
            </div>
          </div>
        </template>
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
</template>

<style lang="scss" scoped>
.search-panel {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  overflow: hidden;
  transition: background-color var(--transition-normal);
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

.modal-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);

  @include forTablet {
    width: 44px;
    height: 44px;
  }

  &:hover,
  &:focus-visible {
    background: var(--color-surface-hover);
    color: var(--color-text);
  }
}

.search-input-wrapper {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 40px;
  padding-left: 12px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast),
    background-color var(--transition-normal);

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
  transition: background-color var(--transition-fast),
    color var(--transition-fast);

  &:hover {
    background: var(--color-primary);
    color: #fff;
  }

  &.active {
    background: var(--color-primary-light);
    color: var(--color-primary);
  }
}

@media screen and (max-width: 639px) {
  .provider-item {
    min-height: 44px;
  }
}

// Filter Section - Chip Cloud
.filter-section {
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-hover);
  flex-shrink: 0;
  transition: background-color var(--transition-normal),
    border-color var(--transition-normal);
}

.filter-category {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 10px;

  &:last-of-type {
    margin-bottom: 0;
  }
}

.category-icon {
  width: 24px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.filter-chip {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  cursor: pointer;
  user-select: none;
  transition: all var(--transition-fast);

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

// Group chips - Blue/Primary
.chip-group {
  background: var(--color-primary-light);
  color: var(--color-primary);

  &:hover:not(.disabled),
  &.active {
    background: var(--color-primary);
    color: #fff;
  }

  &.disabled {
    background: var(--color-surface-hover);
    color: var(--color-text-muted);
    opacity: 0.5;
    cursor: not-allowed;
  }
}

// Resolution chips - Green
.chip-resolution {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);

  &:hover:not(.disabled),
  &.active {
    background: var(--color-success);
    color: #fff;
  }

  &.disabled {
    background: var(--color-surface-hover);
    color: var(--color-text-muted);
    opacity: 0.5;
    cursor: not-allowed;
  }
}

// Subtitle chips - Orange
.chip-subtitle {
  background: rgba(249, 115, 22, 0.15);
  color: var(--color-accent);

  &:hover:not(.disabled),
  &.active {
    background: var(--color-accent);
    color: #fff;
  }

  &.disabled {
    background: var(--color-surface-hover);
    color: var(--color-text-muted);
    opacity: 0.5;
    cursor: not-allowed;
  }
}

// Season chips - Purple
.chip-season {
  background: rgba(139, 92, 246, 0.15);
  color: rgb(139, 92, 246);

  &:hover:not(.disabled),
  &.active {
    background: rgb(139, 92, 246);
    color: #fff;
  }

  &.disabled {
    background: var(--color-surface-hover);
    color: var(--color-text-muted);
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.expand-btn {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-primary);
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }
}

// Filter Summary
.filter-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
  gap: 8px;
}

.selected-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.selected-label {
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.selected-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.selected-chip {
  height: 24px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 500;
  font-family: inherit;
  border: none;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  color: #fff;
  transition: opacity var(--transition-fast);

  &:hover,
  &:focus-visible {
    opacity: 0.8;
  }

  &.chip-group {
    background: var(--color-primary);
  }

  &.chip-resolution {
    background: var(--color-success);
  }

  &.chip-subtitle {
    background: var(--color-accent);
  }

  &.chip-season {
    background: rgb(139, 92, 246);
  }
}

.clear-all-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-family: inherit;
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;

  &:hover {
    border-color: var(--color-danger);
    color: var(--color-danger);
  }
}

.results-count {
  font-size: 12px;
  color: var(--color-text-muted);
  flex-shrink: 0;
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

// Bangumi list - Compact
.bangumi-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bangumi-row {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  transition: border-color var(--transition-fast);
}

.bangumi-poster {
  // Height = 4 rows: 4 * 36px + 3 * 8px = 168px
  // Width = 168px * 5/7 = 120px
  width: 120px;
  height: 168px;
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: var(--radius-sm);
    background: var(--color-surface-hover);
  }
}

.bangumi-poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
}

.placeholder-title {
  font-size: 10px;
  font-weight: 500;
  color: var(--color-text-muted);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  line-height: 1.3;
}

// Variant chips - flex wrap flow layout
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
  gap: 8px;
  height: 36px;
  padding: 0 6px;
  font-family: inherit;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  @include forTouch {
    min-height: 44px;
  }

  &:hover,
  &:focus-visible {
    border-color: var(--color-primary);
    background: var(--color-primary);

    .tag {
      background: rgba(255, 255, 255, 0.2);
      color: #fff;
    }
  }

  &:active {
    transform: scale(0.97);
  }
}

// Display-only tags (non-clickable) - unified with filter chips
.tag {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-full);
  pointer-events: none;
  transition: all var(--transition-fast);
}

.tag-group {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.tag-res {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);
}

.tag-sub {
  background: rgba(249, 115, 22, 0.15);
  color: var(--color-accent);
}

.tag-season {
  background: rgba(139, 92, 246, 0.15);
  color: rgb(139, 92, 246);
}

.variant-expand-btn {
  height: 36px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-primary);
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }
}

@media screen and (max-width: 639px) {
  .modal-header {
    gap: 6px;
    padding: 8px;
  }

  .search-input-wrapper {
    height: var(--touch-target);
    gap: 0;
    padding-left: 0;
  }

  .search-icon-btn {
    width: var(--touch-target);
    height: var(--touch-target);
    flex: 0 0 var(--touch-target);
    justify-content: center;
  }

  .search-input {
    font-size: 16px;
  }

  .provider-btn {
    min-width: 76px;
    padding: 0 10px;
  }

  .provider-item {
    min-height: var(--touch-target);
  }

  .filter-section {
    max-height: min(44dvh, 280px);
    padding: 8px;
    overflow-y: auto;
  }

  .filter-category {
    gap: 4px;
    margin-bottom: 6px;
  }

  .category-icon {
    width: 28px;
    height: var(--touch-target);
  }

  .filter-chips {
    min-width: 0;
    flex: 1;
    flex-wrap: nowrap;
    overflow-x: auto;
    overscroll-behavior-x: contain;
  }

  .filter-chip,
  .expand-btn,
  .selected-chip,
  .clear-all-btn {
    min-height: var(--touch-target);
    flex-shrink: 0;
  }

  .filter-summary {
    align-items: flex-start;
    margin-top: 8px;
    padding-top: 8px;
  }

  .selected-filters {
    align-items: flex-start;
  }

  .selected-chips {
    min-width: 0;
    flex-wrap: nowrap;
    overflow-x: auto;
  }

  .results-container {
    padding: 8px;
    overscroll-behavior-y: contain;
  }

  .empty-state {
    min-height: 160px;
    padding: 20px;
    text-align: center;
  }

  .bangumi-list {
    gap: 8px;
  }

  .bangumi-row {
    gap: 8px;
    padding: 8px;
  }

  .bangumi-poster {
    width: 60px;
    height: 84px;
  }

  .bangumi-variants {
    gap: 6px;
  }

  .variant-chip {
    width: 100%;
    height: auto;
    min-height: var(--touch-target);
    flex-wrap: wrap;
    gap: 4px;
    padding: 5px;
    border-radius: var(--radius-md);
  }

  .tag {
    max-width: 100%;
    height: 22px;
    padding: 0 7px;
    overflow: hidden;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .variant-expand-btn {
    min-height: var(--touch-target);
  }
}

@media (prefers-reduced-motion: reduce) {
  .search-panel,
  .search-panel * {
    scroll-behavior: auto;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
</style>
