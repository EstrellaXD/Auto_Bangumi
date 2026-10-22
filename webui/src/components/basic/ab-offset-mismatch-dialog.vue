<script lang="ts" setup>
import type { OffsetSuggestionDetail, TMDBSummary } from '#/bangumi';

const props = withDefaults(
  defineProps<{
    bangumiTitle: string;
    parsedSeason: number;
    parsedEpisode: number;
    tmdbInfo: TMDBSummary | null;
    suggestion: OffsetSuggestionDetail | null;
  }>(),
  {
    tmdbInfo: null,
    suggestion: null,
  }
);

const emit = defineEmits<{
  (e: 'apply', offsets: { seasonOffset: number; episodeOffset: number }): void;
  (e: 'keep'): void;
  (e: 'cancel'): void;
}>();

const { t } = useMyI18n();

const show = defineModel('show', { default: false });

// Local editable offset values
const seasonOffset = ref(props.suggestion?.season_offset ?? 0);
const episodeOffset = ref(props.suggestion?.episode_offset ?? 0);

// Watch for suggestion changes
watch(
  () => props.suggestion,
  (newVal) => {
    if (newVal) {
      seasonOffset.value = newVal.season_offset;
      episodeOffset.value = newVal.episode_offset;
    }
  }
);

// Preview calculation
const preview = computed(() => {
  const newSeason = props.parsedSeason + seasonOffset.value;
  const newEpisode = props.parsedEpisode + episodeOffset.value;
  const formatNum = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return {
    from: `S${formatNum(props.parsedSeason)}E${formatNum(props.parsedEpisode)}`,
    to: `S${formatNum(Math.max(1, newSeason))}E${formatNum(
      Math.max(1, newEpisode)
    )}`,
  };
});

// 置信度：方块语义标记 + 墨色文字（ab-tag），颜色不承载文字
const CONFIDENCE_TAG = {
  high: 'danger',
  medium: 'warning',
  low: 'neutral',
} as const;

function handleApply() {
  emit('apply', {
    seasonOffset: seasonOffset.value,
    episodeOffset: episodeOffset.value,
  });
  show.value = false;
}

function handleKeep() {
  emit('keep');
  show.value = false;
}

function handleCancel() {
  emit('cancel');
  show.value = false;
}
</script>

<template>
  <ab-modal
    v-model:show="show"
    size="md"
    :title="t('offset.dialog_title')"
    @close="emit('cancel')"
  >
    <!-- Bangumi title -->
    <div class="bangumi-title">
      {{ bangumiTitle }}
    </div>

    <!-- Comparison section：两列共用行轨道（subgrid），标题换行时数值行仍对齐 -->
    <div class="comparison">
      <!-- RSS parsed result -->
      <div class="comparison-box">
        <div class="comparison-label">
          {{ t('offset.parsed_result') }}
        </div>
        <div class="comparison-value">
          <span class="value-label">{{ t('offset.season') }}:</span>
          <span class="value-num">{{ parsedSeason }}</span>
        </div>
        <div class="comparison-value">
          <span class="value-label">{{ t('offset.episode') }}:</span>
          <span class="value-num">{{ parsedEpisode }}</span>
        </div>
      </div>

      <div class="comparison-vs">
        &ne;
      </div>

      <!-- TMDB data -->
      <div class="comparison-box">
        <div class="comparison-label">
          {{ t('offset.tmdb_data') }}
        </div>
        <div v-if="tmdbInfo" class="comparison-value">
          <span class="value-label">{{ t('offset.total_seasons') }}:</span>
          <span class="value-num">{{ tmdbInfo.total_seasons }}</span>
        </div>
        <div
          v-if="
            tmdbInfo
              && tmdbInfo.season_episode_counts[
                parsedSeason + (suggestion?.season_offset ?? 0)
              ]
          "
          class="comparison-value"
        >
          <span class="value-label">S{{ parsedSeason + (suggestion?.season_offset ?? 0) }}
            {{ t('offset.episode') }}:</span>
          <span class="value-num">{{
            tmdbInfo.season_episode_counts[
              parsedSeason + (suggestion?.season_offset ?? 0)
            ]
          }}</span>
        </div>
      </div>
    </div>

    <!-- Reason -->
    <div v-if="suggestion?.reason" class="reason-section">
      <ab-tag
        class="reason-badge"
        :type="CONFIDENCE_TAG[suggestion.confidence]"
        :title="suggestion.confidence"
      />
      <span class="reason-text">{{ suggestion.reason }}</span>
    </div>

    <!-- Offset inputs -->
    <div class="offset-section">
      <div class="offset-title">
        {{ t('offset.suggested_offset') }}
      </div>
      <div class="offset-row">
        <span class="offset-label">{{ t('offset.season_offset') }}:</span>
        <ab-input
          v-model="seasonOffset"
          type="number"
          class="offset-input"
          :aria-label="t('offset.season_offset')"
        />
        <span class="offset-hint">&rarr; S{{ parsedSeason }}
          {{ t('offset.season') === '季度' ? '变为' : 'becomes' }} S{{
            Math.max(1, parsedSeason + seasonOffset)
          }}</span>
      </div>
      <div class="offset-row">
        <span class="offset-label">{{ t('offset.episode_offset') }}:</span>
        <ab-input
          v-model="episodeOffset"
          type="number"
          class="offset-input"
          :aria-label="t('offset.episode_offset')"
        />
        <span class="offset-hint">&rarr; E{{ parsedEpisode }}
          {{ t('offset.season') === '季度' ? '保持' : 'stays' }} E{{
            Math.max(1, parsedEpisode + episodeOffset)
          }}</span>
      </div>
    </div>

    <!-- Preview -->
    <div class="preview-section">
      <span class="preview-label">{{ t('offset.preview') }}:</span>
      <span class="preview-from">{{ preview.from }}</span>
      <span class="preview-arrow">&rarr;</span>
      <span class="preview-to">{{ preview.to }}</span>
    </div>

    <template #footer>
      <ab-button size="sm" variant="ghost" @click="handleCancel">
        {{ t('offset.cancel') }}
      </ab-button>
      <ab-button size="sm" variant="secondary" @click="handleKeep">
        {{ t('offset.keep') }}
      </ab-button>
      <ab-button size="sm" variant="primary" @click="handleApply">
        {{ t('offset.apply') }}
      </ab-button>
    </template>
  </ab-modal>
</template>

<style lang="scss" scoped>
.bangumi-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
}

.comparison {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  grid-template-rows: repeat(3, auto);
  column-gap: 12px;
  margin-bottom: 16px;
}

.comparison-box {
  display: grid;
  grid-row: span 3;
  grid-template-rows: subgrid;
  row-gap: 4px;
  min-width: 0;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.comparison-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
}

.comparison-value {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;

  .value-label {
    color: var(--color-text-secondary);
  }

  .value-num {
    font-weight: 600;
    color: var(--color-text);
    font-variant-numeric: tabular-nums;
  }
}

.comparison-vs {
  grid-row: span 3;
  display: flex;
  align-items: center;
  font-size: 20px;
  color: var(--color-text-muted);
}

.reason-section {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.reason-badge {
  flex-shrink: 0;
  text-transform: uppercase;
}

.reason-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.offset-section {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.offset-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
}

.offset-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.offset-label {
  flex-shrink: 0;
  width: 100px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.offset-input {
  flex-shrink: 0;
  width: 72px;
}

.offset-hint {
  flex: 1;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.preview-section {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  border-radius: var(--radius-md);
}

.preview-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.preview-from {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.preview-arrow {
  font-size: 18px;
  color: var(--color-primary);
}

.preview-to {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-primary);
}
</style>
