<script lang="ts" setup>
import { CheckOne, CloseOne } from '@icon-park/vue-next';
import { NSpin, NTooltip } from 'naive-ui';
import type { RSSPreviewItem } from '#/rss';

const props = defineProps<{
  rssLink: string;
  ruleFilter: string[];
}>();

const show = defineModel<boolean>('show', { default: false });

const { t } = useMyI18n();

const rssPreviewLoading = ref(false);
const rssPreviewError = ref(false);
const rssPreviewItems = ref<RSSPreviewItem[]>([]);
const globalFilter = ref<string[]>([]);
const showBlockedItems = ref(true);
let rssPreviewRequestToken = 0;

type FilteredRSSPreviewItem = RSSPreviewItem & {
  passesFilter: boolean;
};

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function compileFilterTerms(terms: string[], ignoreCase: boolean) {
  const normalizedTerms = terms.map((term) => term.trim()).filter(Boolean);
  if (normalizedTerms.length === 0) return null;

  const flags = ignoreCase ? 'i' : '';
  try {
    return new RegExp(normalizedTerms.join('|'), flags);
  } catch {
    return new RegExp(
      normalizedTerms.map((term) => escapeRegExp(term)).join('|'),
      flags
    );
  }
}

function applyRssPreviewFilters(
  items: RSSPreviewItem[],
  ruleFilter: string[],
  globalFilter: string[]
): FilteredRSSPreviewItem[] {
  const localPattern = compileFilterTerms(ruleFilter, true);
  const globalPattern = compileFilterTerms(globalFilter, false);

  return items.map((item) => ({
    ...item,
    passesFilter: !(
      (globalPattern && globalPattern.test(item.name)) ||
      (localPattern && localPattern.test(item.name))
    ),
  }));
}

function normalizeFilters(filters: string[]) {
  return filters.map((value) => value.trim()).filter(Boolean);
}

const previewFilters = computed(() =>
  [
    ...normalizeFilters(globalFilter.value),
    ...normalizeFilters(props.ruleFilter),
  ].filter((value, index, values) => values.indexOf(value) === index)
);

const previewRows = computed(() =>
  applyRssPreviewFilters(
    rssPreviewItems.value,
    props.ruleFilter,
    globalFilter.value
  )
);

const blockedCount = computed(
  () => previewRows.value.filter((item) => !item.passesFilter).length
);

const visiblePreviewRows = computed(() =>
  showBlockedItems.value
    ? previewRows.value
    : previewRows.value.filter((item) => item.passesFilter)
);

function previewStatusLabel(passesFilter: boolean) {
  return t(
    passesFilter
      ? 'search.confirm.preview_passed'
      : 'search.confirm.preview_blocked'
  );
}

function resetPreview() {
  rssPreviewLoading.value = false;
  rssPreviewError.value = false;
  rssPreviewItems.value = [];
  globalFilter.value = [];
  showBlockedItems.value = true;
  rssPreviewRequestToken += 1;
}

async function loadRssPreview() {
  if (!props.rssLink) {
    resetPreview();
    return;
  }

  const requestToken = ++rssPreviewRequestToken;
  rssPreviewLoading.value = true;
  rssPreviewError.value = false;

  try {
    const preview = await apiRSS.preview(props.rssLink);
    if (requestToken !== rssPreviewRequestToken) return;
    rssPreviewItems.value = preview.items;
    globalFilter.value = preview.global_filter;
  } catch (e) {
    if (requestToken !== rssPreviewRequestToken) return;
    console.error('Failed to load RSS preview:', e);
    rssPreviewItems.value = [];
    globalFilter.value = [];
    rssPreviewError.value = true;
  } finally {
    if (requestToken === rssPreviewRequestToken) {
      rssPreviewLoading.value = false;
    }
  }
}

watch(
  () => props.rssLink,
  () => {
    resetPreview();
    if (show.value) {
      loadRssPreview();
    }
  }
);

watch(show, (visible) => {
  if (!visible) {
    rssPreviewRequestToken += 1;
    rssPreviewLoading.value = false;
    showBlockedItems.value = true;
    return;
  }

  if (rssPreviewItems.value.length > 0 && !rssPreviewError.value) {
    return;
  }

  loadRssPreview();
});

onBeforeUnmount(() => {
  rssPreviewRequestToken += 1;
});
</script>

<template>
  <ab-modal
    v-model:show="show"
    :title="$t('search.confirm.preview_title')"
    size="lg"
    max-height="78dvh"
    mobile-fullscreen
  >
    <div class="rss-preview-dialog">
      <section class="rss-preview-filters">
        <div class="rss-preview-filters__header">
          {{ $t('search.confirm.filter') }}
        </div>
        <div v-if="previewFilters.length > 0" class="rss-preview-filters__list">
          <span
            v-for="filter in previewFilters"
            :key="filter"
            class="rss-preview-filter-tag"
          >
            <span class="rss-preview-filter-tag__value">{{ filter }}</span>
          </span>
        </div>
        <div v-else class="rss-preview-filters__empty">
          {{ $t('search.confirm.preview_filter_empty') }}
        </div>
      </section>

      <div v-if="rssPreviewLoading" class="rss-preview-state">
        <NSpin :size="18" />
        <span>{{ t('search.confirm.preview_loading') }}</span>
      </div>
      <div
        v-else-if="rssPreviewError"
        class="rss-preview-state rss-preview-state--error"
      >
        {{ t('search.confirm.preview_failed') }}
      </div>
      <div v-else-if="previewRows.length === 0" class="rss-preview-state">
        {{ t('search.confirm.preview_empty') }}
      </div>
      <div v-else class="rss-preview-table">
        <div class="rss-preview-toolbar">
          <div class="toolbar-stat">
            <span>{{
              t('search.confirm.preview_total_count', {
                count: previewRows.length,
              })
            }}</span>
            <span
              v-if="!showBlockedItems && blockedCount > 0"
              class="filtered-text"
            >
              {{
                t('search.confirm.preview_hidden_blocked', {
                  count: blockedCount,
                })
              }}
            </span>
          </div>
          <button
            v-if="blockedCount > 0"
            type="button"
            class="rss-preview-toggle-btn"
            :aria-pressed="showBlockedItems"
            @click="showBlockedItems = !showBlockedItems"
          >
            {{
              showBlockedItems
                ? t('search.confirm.preview_hide_blocked')
                : t('search.confirm.preview_show_blocked')
            }}
          </button>
        </div>

        <div
          v-if="visiblePreviewRows.length === 0"
          class="rss-preview-state rss-preview-state--compact"
        >
          {{ t('search.confirm.preview_empty_visible') }}
        </div>
        <table v-else class="rss-preview-table__table">
          <tbody>
            <tr
              v-for="item in visiblePreviewRows"
              :key="`${item.url}::${item.name}`"
              class="rss-preview-table-row"
            >
              <td class="rss-preview-table-cell">
                <div class="rss-preview-name-cell">
                  <NTooltip>
                    <template #trigger>
                      <span
                        class="rss-preview-status"
                        :class="
                          item.passesFilter
                            ? 'rss-preview-status--passed'
                            : 'rss-preview-status--blocked'
                        "
                        :title="previewStatusLabel(item.passesFilter)"
                        :aria-label="previewStatusLabel(item.passesFilter)"
                      >
                        <CheckOne
                          v-if="item.passesFilter"
                          theme="filled"
                          size="16"
                          :fill="['var(--color-success)']"
                        />
                        <CloseOne
                          v-else
                          theme="filled"
                          size="16"
                          :fill="['var(--color-danger)']"
                        />
                      </span>
                    </template>
                    {{ previewStatusLabel(item.passesFilter) }}
                  </NTooltip>
                  <span class="rss-preview-name">{{ item.name }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </ab-modal>
</template>

<style lang="scss" scoped>
.rss-preview-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rss-preview-filters {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
}

.rss-preview-filters__header {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.rss-preview-filters__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rss-preview-filter-tag {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
}

.rss-preview-filter-tag__value {
  min-width: 0;
  word-break: break-word;
}

.rss-preview-filters__empty {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.rss-preview-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 220px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
  text-align: center;

  &--error {
    color: var(--color-danger);
  }

  &--compact {
    min-height: 96px;
  }
}

.rss-preview-table {
  overflow: hidden;
  background: var(--color-surface);
  border-radius: var(--radius-md);
}

.rss-preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-hover);
}

.toolbar-stat {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.filtered-text {
  color: var(--color-text-muted);
}

.rss-preview-toggle-btn {
  flex-shrink: 0;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--transition-fast), color var(--transition-fast),
    background-color var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }
}

.rss-preview-table__table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.rss-preview-table-row:first-child .rss-preview-table-cell {
  border-top: none;
}

.rss-preview-table-cell {
  padding: 12px 16px;
  font-size: 13px;
  vertical-align: top;
  border-top: 1px solid var(--color-border);
}

.rss-preview-name-cell {
  display: flex;
  align-items: start;
  gap: 10px;
  width: 100%;
  min-width: 0;
}

.rss-preview-name {
  min-width: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text);
  white-space: normal;
  word-break: break-word;
}

.rss-preview-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-top: 2px;

  &--passed {
    color: var(--color-success);
  }

  &--blocked {
    color: var(--color-danger);
  }
}

:deep(.ab-modal) {
  z-index: calc(var(--z-modal) + 20);
}

:deep(.ab-modal-backdrop) {
  z-index: calc(var(--z-modal) + 19);
}

:deep(.ab-modal-wrapper) {
  z-index: calc(var(--z-modal) + 20);
}

:deep(.ab-bottom-sheet) {
  z-index: calc(var(--z-modal) + 20);
}

:deep(.ab-bottom-sheet__backdrop) {
  z-index: calc(var(--z-modal) + 19);
}

:deep(.ab-bottom-sheet__container) {
  z-index: calc(var(--z-modal) + 20);
}
</style>
