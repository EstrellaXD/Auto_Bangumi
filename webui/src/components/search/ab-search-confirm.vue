<script lang="ts" setup>
import {
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Copy,
  ImageOff,
} from '@lucide/vue';
import { NCollapseTransition, NDynamicTags, useMessage } from 'naive-ui';
import type {
  BangumiRule,
  DetectOffsetResponse,
  OffsetSuggestionDetail,
  TMDBSummary,
} from '#/bangumi';

const props = defineProps<{
  bangumi: BangumiRule;
  /** 由父组件控制显隐，关闭时保持挂载，让 ab-modal 的离场过渡跑完 */
  show: boolean;
}>();

const emit = defineEmits<{
  (e: 'confirm', bangumi: BangumiRule): void;
  (e: 'cancel'): void;
}>();

const message = useMessage();
const { t } = useMyI18n();

// Local deep copy of bangumi for editing (prevents mutation of original prop)
const localBangumi = ref<BangumiRule>(
  JSON.parse(JSON.stringify(props.bangumi))
);

const posterSrc = computed(() =>
  resolvePosterUrl(localBangumi.value.poster_link)
);
const showAdvanced = ref(false);
const offsetLoading = ref(false);

// Offset mismatch detection state
const showOffsetDialog = ref(false);
const offsetSuggestion = ref<OffsetSuggestionDetail | null>(null);
const tmdbInfo = ref<TMDBSummary | null>(null);

// 每次打开时从 prop 重新拷贝并检测偏移（组件在关闭后保持挂载）
watch(
  () => props.show,
  (open) => {
    if (!open) {
      showOffsetDialog.value = false;
      return;
    }
    localBangumi.value = JSON.parse(JSON.stringify(props.bangumi));
    detectOffsetMismatch();
  }
);

// Detect offset mismatch on mount
async function detectOffsetMismatch() {
  if (!localBangumi.value.official_title || !localBangumi.value.season) return;

  // 组件关闭后保持挂载：晚到的结果只在同一次打开里有效
  const target = localBangumi.value;
  try {
    const result: DetectOffsetResponse = await apiBangumi.detectOffset({
      title: target.official_title,
      parsed_season: target.season,
      parsed_episode: 1, // Use episode 1 as baseline for detection
    });
    if (!props.show || localBangumi.value !== target) return;

    if (result.has_mismatch && result.suggestion) {
      offsetSuggestion.value = result.suggestion;
      tmdbInfo.value = result.tmdb_info;
      showOffsetDialog.value = true;
    }
  } catch (e) {
    console.error('Failed to detect offset mismatch:', e);
  }
}

// Handle offset dialog apply
function handleOffsetApply(offsets: {
  seasonOffset: number;
  episodeOffset: number;
}) {
  localBangumi.value.season_offset = offsets.seasonOffset;
  localBangumi.value.episode_offset = offsets.episodeOffset;
  showOffsetDialog.value = false;
}

// Handle offset dialog keep (no change)
function handleOffsetKeep() {
  showOffsetDialog.value = false;
}

// Handle offset dialog cancel
function handleOffsetCancel() {
  showOffsetDialog.value = false;
}

// Run detection on mount
onMounted(() => {
  if (props.show) detectOffsetMismatch();
});

// Info tags for display (just values, no labels)
// 标记色与搜索结果一致：组=info、分辨率=success、字幕=warning、季=neutral
const infoTags = computed(() => {
  const tags: {
    value: string;
    type: string;
    tagType: 'info' | 'success' | 'warning' | 'neutral';
  }[] = [];
  const { season, season_raw, dpi, subtitle, group_name } = localBangumi.value;

  if (season || season_raw) {
    const seasonDisplay = season_raw || (season ? `第${season}季` : '');
    tags.push({ value: seasonDisplay, type: 'season', tagType: 'neutral' });
  }

  if (dpi) {
    tags.push({ value: dpi, type: 'resolution', tagType: 'success' });
  }

  if (subtitle) {
    tags.push({ value: subtitle, type: 'subtitle', tagType: 'warning' });
  }

  if (group_name) {
    tags.push({ value: group_name, type: 'group', tagType: 'info' });
  }

  return tags;
});

// Copy RSS link
const { copy, copied } = useClipboard({ copiedDuring: 2000, legacy: true });

async function copyRssLink() {
  const rssLink = localBangumi.value.rss_link?.[0] || '';
  if (rssLink) {
    await copy(rssLink);
  }
}

// Auto detect offset
async function autoDetectOffset() {
  if (!localBangumi.value.id) return;
  offsetLoading.value = true;
  try {
    const result = await apiBangumi.suggestOffset(localBangumi.value.id);
    localBangumi.value.episode_offset = result.suggested_offset;
  } catch (e) {
    console.error('Failed to detect offset:', e);
    message.error(t('offset.detect_failed'));
  } finally {
    offsetLoading.value = false;
  }
}

function handleConfirm() {
  emit('confirm', localBangumi.value);
}
</script>

<template>
  <ab-modal
    :show="show"
    size="md"
    :title="$t('search.confirm.title')"
    @update:show="(value: boolean) => value || emit('cancel')"
  >
    <!-- Bangumi Info -->
    <div class="bangumi-info">
      <div class="bangumi-poster">
        <template v-if="localBangumi.poster_link">
          <img :src="posterSrc" :alt="localBangumi.official_title">
        </template>
        <template v-else>
          <div class="poster-placeholder">
            <ImageOff :size="32" />
          </div>
        </template>
      </div>
      <div class="bangumi-meta">
        <h3 class="bangumi-title">
          {{ localBangumi.official_title }}
        </h3>
        <p v-if="localBangumi.title_raw" class="bangumi-subtitle">
          {{ localBangumi.title_raw }}
        </p>
        <p v-if="localBangumi.year" class="bangumi-year">
          {{ localBangumi.year }}
        </p>
      </div>
    </div>

    <!-- Info Tags -->
    <div v-if="infoTags.length > 0" class="info-tags">
      <ab-tag v-for="tag in infoTags" :key="tag.type" :type="tag.tagType">
        {{ tag.value }}
      </ab-tag>
    </div>

    <!-- RSS Link -->
    <div class="rss-section">
      <div class="info-row">
        <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
        <span class="info-value info-value--link">
          {{ localBangumi.rss_link?.[0] || '-' }}
        </span>
        <button
          class="copy-btn"
          :class="{ copied }"
          :aria-label="$t('search.confirm.copy_rss')"
          @click="copyRssLink"
        >
          <CircleCheck v-if="copied" :size="14" />
          <Copy v-else :size="14" />
        </button>
      </div>
    </div>

    <!-- Advanced settings -->
    <div class="advanced-section">
      <button
        class="advanced-toggle"
        :aria-expanded="showAdvanced"
        @click="showAdvanced = !showAdvanced"
      >
        <component
          :is="showAdvanced ? ChevronDown : ChevronRight"
          :size="14"
        />
        {{ $t('search.confirm.advanced') }}
      </button>

      <!-- 与 ab-fold-panel 同一高度过渡 -->
      <NCollapseTransition :show="showAdvanced">
        <!-- 两列网格：标签一列，控件统一左对齐在第二列 -->
        <div class="advanced-content">
          <label class="advanced-label">{{ $t('search.confirm.filter') }}</label>
          <div class="advanced-control filter-tags">
            <NDynamicTags v-model:value="localBangumi.filter" size="small" />
          </div>

          <label class="advanced-label">{{
            $t('homepage.rule.season_offset')
          }}</label>
          <div class="advanced-control">
            <ab-input
              v-model="localBangumi.season_offset"
              type="number"
              class="offset-input"
            />
          </div>

          <label class="advanced-label">{{
            $t('homepage.rule.episode_offset')
          }}</label>
          <div class="advanced-control">
            <ab-input
              v-model="localBangumi.episode_offset"
              type="number"
              class="offset-input"
            />
            <ab-button
              size="sm"
              :loading="offsetLoading"
              @click="autoDetectOffset"
            >
              {{ $t('homepage.rule.auto_detect') }}
            </ab-button>
          </div>
        </div>
      </NCollapseTransition>
    </div>

    <template #footer>
      <ab-button @click="emit('cancel')">
        {{ $t('common.cancel') }}
      </ab-button>
      <ab-button variant="primary" @click="handleConfirm">
        {{ $t('search.confirm.subscribe') }}
      </ab-button>
    </template>
  </ab-modal>

  <!-- Offset Mismatch Dialog -->
  <ab-offset-mismatch-dialog
    v-model:show="showOffsetDialog"
    :bangumi-title="localBangumi.official_title"
    :parsed-season="localBangumi.season"
    :parsed-episode="1"
    :tmdb-info="tmdbInfo"
    :suggestion="offsetSuggestion"
    @apply="handleOffsetApply"
    @keep="handleOffsetKeep"
    @cancel="handleOffsetCancel"
  />
</template>

<style lang="scss" scoped>
// Bangumi info section
.bangumi-info {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.bangumi-poster {
  width: 80px;
  height: 112px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface-hover);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.bangumi-meta {
  flex: 1;
  min-width: 0;
}

.bangumi-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
  line-height: 1.4;
}

.bangumi-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bangumi-year {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 4px 0 0;
}

// Info Tags
.info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

// RSS section
.rss-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.info-label {
  flex-shrink: 0;
  width: 70px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.info-value {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: var(--color-text);
  word-break: break-all;

  &--link {
    color: var(--color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.copy-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  &.copied {
    background: var(--color-success);
    border-color: var(--color-success);
    color: #fff;
  }
}

// Advanced section
.advanced-section {
  margin-bottom: 8px;
}

.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color var(--transition-fast);

  &:hover {
    color: var(--color-text);
  }
}

.advanced-content {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px 16px;
  padding: 16px;
  // surface 底加发丝边框：内部 surface-2 填充的输入框和按钮才有可见边界
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-top: 8px;
}

.advanced-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.advanced-control {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  :deep(.n-dynamic-tags) {
    min-height: 32px;
    align-items: center;

    .n-tag {
      height: 28px;
      margin: 2px 6px 2px 0 !important;
    }

    .n-button {
      height: 28px;
    }
  }
}

.offset-input {
  width: 80px;
}
</style>
