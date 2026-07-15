<script lang="ts" setup>
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionRoot,
} from '@headlessui/vue';
import { Caution, Close } from '@icon-park/vue-next';
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
  (e: 'after-leave'): void;
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

// Confidence badge color
const confidenceColor = computed(() => {
  switch (props.suggestion?.confidence) {
    case 'high':
      return 'var(--color-error)';
    case 'medium':
      return 'var(--color-warning)';
    default:
      return 'var(--color-text-muted)';
  }
});

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
  <TransitionRoot
    appear
    :show="show"
    as="template"
    enter="modal-enter-active"
    enter-from="modal-enter-from"
    enter-to="modal-enter-to"
    leave="modal-leave-active"
    leave-from="modal-leave-from"
    leave-to="modal-leave-to"
    @after-leave="emit('after-leave')"
  >
    <Dialog class="offset-dialog" @close="handleCancel">
      <div class="dialog-backdrop">
        <DialogPanel as="template">
          <div class="dialog-modal">
            <!-- Header -->
            <header class="dialog-header">
              <div class="header-icon">
                <Caution theme="filled" size="20" />
              </div>
              <DialogTitle as="template">
                <h2 class="dialog-title">{{ t('offset.dialog_title') }}</h2>
              </DialogTitle>
              <button
                class="close-btn"
                :aria-label="t('common.close')"
                @click="handleCancel"
              >
                <Close theme="outline" size="18" />
              </button>
            </header>

            <!-- Content -->
            <div class="dialog-content">
              <!-- Bangumi title -->
              <div class="bangumi-title">{{ bangumiTitle }}</div>

              <!-- Comparison section -->
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

                <div class="comparison-vs">&ne;</div>

                <!-- TMDB data -->
                <div class="comparison-box">
                  <div class="comparison-label">
                    {{ t('offset.tmdb_data') }}
                  </div>
                  <div v-if="tmdbInfo" class="comparison-value">
                    <span class="value-label"
                      >{{ t('offset.total_seasons') }}:</span
                    >
                    <span class="value-num">{{ tmdbInfo.total_seasons }}</span>
                  </div>
                  <div
                    v-if="
                      tmdbInfo &&
                      tmdbInfo.season_episode_counts[
                        parsedSeason + (suggestion?.season_offset ?? 0)
                      ]
                    "
                    class="comparison-value"
                  >
                    <span class="value-label"
                      >S{{ parsedSeason + (suggestion?.season_offset ?? 0) }}
                      {{ t('offset.episode') }}:</span
                    >
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
                <span
                  class="reason-badge"
                  :style="{ backgroundColor: confidenceColor }"
                >
                  {{ suggestion.confidence }}
                </span>
                <span class="reason-text">{{ suggestion.reason }}</span>
              </div>

              <!-- Offset inputs -->
              <div class="offset-section">
                <div class="offset-title">
                  {{ t('offset.suggested_offset') }}
                </div>
                <div class="offset-row">
                  <label class="offset-label"
                    >{{ t('offset.season_offset') }}:</label
                  >
                  <input
                    v-model.number="seasonOffset"
                    type="number"
                    class="offset-input"
                  />
                  <span class="offset-hint"
                    >&rarr; S{{ parsedSeason }}
                    {{ t('offset.season') === '季度' ? '变为' : 'becomes' }} S{{
                      Math.max(1, parsedSeason + seasonOffset)
                    }}</span
                  >
                </div>
                <div class="offset-row">
                  <label class="offset-label"
                    >{{ t('offset.episode_offset') }}:</label
                  >
                  <input
                    v-model.number="episodeOffset"
                    type="number"
                    class="offset-input"
                  />
                  <span class="offset-hint"
                    >&rarr; E{{ parsedEpisode }}
                    {{ t('offset.season') === '季度' ? '保持' : 'stays' }} E{{
                      Math.max(1, parsedEpisode + episodeOffset)
                    }}</span
                  >
                </div>
              </div>

              <!-- Preview -->
              <div class="preview-section">
                <span class="preview-label">{{ t('offset.preview') }}:</span>
                <span class="preview-from">{{ preview.from }}</span>
                <span class="preview-arrow">&rarr;</span>
                <span class="preview-to">{{ preview.to }}</span>
              </div>
            </div>

            <!-- Footer -->
            <footer class="dialog-footer">
              <ab-button size="sm" variant="secondary" @click="handleCancel">
                {{ t('offset.cancel') }}
              </ab-button>
              <ab-button variant="primary" size="sm" @click="handleKeep">
                {{ t('offset.keep') }}
              </ab-button>
              <ab-button size="sm" variant="primary" @click="handleApply">
                {{ t('offset.apply') }}
              </ab-button>
            </footer>
          </div>
        </DialogPanel>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<style lang="scss" scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay);
  z-index: var(--z-modal);
  padding: 16px;
}

.dialog-modal {
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--color-surface-2);
  color: var(--color-warning);
  border-radius: var(--radius-sm);
}

.dialog-title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
    color: var(--color-text);
  }
}

.dialog-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.bangumi-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 16px;
  text-align: center;
}

.comparison {
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-bottom: 16px;
}

.comparison-box {
  flex: 1;
  padding: 12px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.comparison-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
}

.comparison-value {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 4px;

  .value-label {
    color: var(--color-text-muted);
  }

  .value-num {
    font-weight: 600;
    color: var(--color-text);
  }
}

.comparison-vs {
  display: flex;
  align-items: center;
  font-size: 24px;
  color: var(--color-warning);
  font-weight: bold;
}

.reason-section {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.reason-badge {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  color: white;
  text-transform: uppercase;
}

.reason-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.offset-section {
  padding: 16px;
  background: var(--color-surface-hover);
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
  width: 70px;
  height: 32px;
  padding: 0 8px;
  font-size: 14px;
  text-align: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);

  &:focus {
    outline: none;
    border-color: var(--color-primary);
  }
}

.offset-hint {
  flex: 1;
  font-size: 12px;
  color: var(--color-text-muted);
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

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}

// Modal transition
.modal-enter-active,
.modal-leave-active {
  transition: opacity 200ms ease;

  .dialog-modal {
    transition: transform 200ms ease, opacity 200ms ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .dialog-modal {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
}

@media screen and (max-width: 639px) {
  .dialog-backdrop {
    align-items: flex-end;
    padding: 0 env(safe-area-inset-right) 0 env(safe-area-inset-left);
  }

  .dialog-modal {
    max-width: none;
    max-height: calc(
      100dvh - env(safe-area-inset-top) - env(safe-area-inset-bottom)
    );
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;

    @supports not (max-height: 1dvh) {
      max-height: calc(
        100vh - env(safe-area-inset-top) - env(safe-area-inset-bottom)
      );
    }
  }

  .dialog-header {
    padding: 10px 12px 10px 16px;
  }

  .close-btn {
    flex-shrink: 0;
    width: var(--touch-target);
    height: var(--touch-target);
  }

  .dialog-content {
    min-height: 0;
    padding: 16px;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .comparison {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }

  .comparison-vs {
    min-height: 24px;
    justify-content: center;
  }

  .offset-section {
    padding: 12px;
  }

  .offset-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 72px;
  }

  .offset-label {
    width: auto;
  }

  .offset-input {
    width: 72px;
    height: var(--touch-target);
  }

  .offset-hint {
    grid-column: 1 / -1;
  }

  .preview-section {
    flex-wrap: wrap;
    gap: 8px;
  }

  .dialog-footer {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding: 12px 16px max(12px, env(safe-area-inset-bottom));

    :deep(.ab-btn) {
      width: 100%;
      height: auto;
      min-height: var(--touch-target);
      padding: 6px;
      white-space: normal;
      line-height: 1.2;
    }
  }
}
</style>
