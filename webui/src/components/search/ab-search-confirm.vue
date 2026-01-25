<script lang="ts" setup>
import { CheckOne, Close, Copy, Down, ErrorPicture, Right } from '@icon-park/vue-next';
import { NDynamicTags, NSpin, useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';

const message = useMessage();

const props = defineProps<{
  bangumi: BangumiRule;
}>();

const emit = defineEmits<{
  (e: 'confirm', bangumi: BangumiRule): void;
  (e: 'cancel'): void;
}>();

// Local deep copy of bangumi for editing (prevents mutation of original prop)
const localBangumi = ref<BangumiRule>(JSON.parse(JSON.stringify(props.bangumi)));

// Sync when props change
watch(() => props.bangumi, (newVal) => {
  localBangumi.value = JSON.parse(JSON.stringify(newVal));
}, { deep: true });

const posterSrc = computed(() => resolvePosterUrl(localBangumi.value.poster_link));
const showAdvanced = ref(false);
const copied = ref(false);
const offsetLoading = ref(false);

// Info tags for display (just values, no labels)
const infoTags = computed(() => {
  const tags: { value: string; type: string }[] = [];
  const { season, season_raw, dpi, subtitle, group_name } = localBangumi.value;

  if (season || season_raw) {
    const seasonDisplay = season_raw || (season ? `第${season}季` : '');
    tags.push({ value: seasonDisplay, type: 'season' });
  }

  if (dpi) {
    tags.push({ value: dpi, type: 'resolution' });
  }

  if (subtitle) {
    tags.push({ value: subtitle, type: 'subtitle' });
  }

  if (group_name) {
    tags.push({ value: group_name, type: 'group' });
  }

  return tags;
});

// Copy RSS link
async function copyRssLink() {
  const rssLink = localBangumi.value.rss_link?.[0] || '';
  if (rssLink) {
    await navigator.clipboard.writeText(rssLink);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  }
}

// Auto detect offset
async function autoDetectOffset() {
  if (!localBangumi.value.id) return;
  offsetLoading.value = true;
  try {
    const result = await apiBangumi.suggestOffset(localBangumi.value.id);
    localBangumi.value.offset = result.suggested_offset;
  } catch (e) {
    console.error('Failed to detect offset:', e);
    message.error('Failed to detect offset');
  } finally {
    offsetLoading.value = false;
  }
}

function handleConfirm() {
  emit('confirm', localBangumi.value);
}
</script>

<template>
  <div class="confirm-backdrop" @click.self="emit('cancel')">
    <div class="confirm-modal" role="dialog" aria-modal="true">
      <!-- Header -->
      <header class="confirm-header">
        <h2 class="confirm-title">{{ $t('search.confirm.title') }}</h2>
        <button class="close-btn" aria-label="Close" @click="emit('cancel')">
          <Close theme="outline" size="18" />
        </button>
      </header>

      <!-- Content -->
      <div class="confirm-content">
        <!-- Bangumi Info -->
        <div class="bangumi-info">
          <div class="bangumi-poster">
            <template v-if="localBangumi.poster_link">
              <img :src="posterSrc" :alt="localBangumi.official_title" />
            </template>
            <template v-else>
              <div class="poster-placeholder">
                <ErrorPicture theme="outline" size="32" />
              </div>
            </template>
          </div>
          <div class="bangumi-meta">
            <h3 class="bangumi-title">{{ localBangumi.official_title }}</h3>
            <p v-if="localBangumi.title_raw" class="bangumi-subtitle">{{ localBangumi.title_raw }}</p>
            <p v-if="localBangumi.year" class="bangumi-year">{{ localBangumi.year }}</p>
          </div>
        </div>

        <!-- Info Tags -->
        <div v-if="infoTags.length > 0" class="info-tags">
          <div
            v-for="tag in infoTags"
            :key="tag.type"
            class="info-tag"
            :class="`info-tag--${tag.type}`"
          >
            {{ tag.value }}
          </div>
        </div>

        <!-- RSS Link -->
        <div class="rss-section">
          <div class="info-row">
            <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
            <span class="info-value info-value--link">
              {{ localBangumi.rss_link?.[0] || '-' }}
            </span>
            <button class="copy-btn" :class="{ copied }" @click="copyRssLink">
              <CheckOne v-if="copied" theme="outline" size="14" />
              <Copy v-else theme="outline" size="14" />
            </button>
          </div>
        </div>

        <!-- Advanced settings -->
        <div class="advanced-section">
          <button class="advanced-toggle" @click="showAdvanced = !showAdvanced">
            <component :is="showAdvanced ? Down : Right" theme="outline" size="14" />
            {{ $t('search.confirm.advanced') }}
          </button>

          <transition name="expand">
            <div v-show="showAdvanced" class="advanced-content">
              <!-- Filter rules row -->
              <div class="advanced-row advanced-row--tags">
                <label class="advanced-label">{{ $t('search.confirm.filter') }}</label>
                <div class="advanced-control filter-tags">
                  <NDynamicTags v-model:value="localBangumi.filter" size="small" />
                </div>
              </div>

              <!-- Offset row -->
              <div class="advanced-row">
                <label class="advanced-label">{{ $t('homepage.rule.offset') }}</label>
                <div class="advanced-control offset-controls">
                  <input
                    v-model.number="localBangumi.offset"
                    type="number"
                    ab-input
                    class="offset-input"
                  />
                  <button
                    class="detect-btn"
                    :disabled="offsetLoading"
                    @click="autoDetectOffset"
                  >
                    <NSpin v-if="offsetLoading" :size="14" />
                    <span v-else>{{ $t('homepage.rule.auto_detect') }}</span>
                  </button>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>

      <!-- Footer -->
      <footer class="confirm-footer">
        <button class="btn btn-secondary" @click="emit('cancel')">
          {{ $t('common.cancel') }}
        </button>
        <button class="btn btn-primary" @click="handleConfirm">
          {{ $t('search.confirm.subscribe') }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay);
  z-index: calc(var(--z-modal) + 10);
  padding: 16px;
}

.confirm-modal {
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: modal-in 200ms ease-out;
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.confirm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.confirm-title {
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

.confirm-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

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

.info-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;

  &--season {
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
  }

  &--resolution {
    background: color-mix(in srgb, var(--color-accent) 12%, transparent);
    color: var(--color-accent);
  }

  &--subtitle {
    background: color-mix(in srgb, var(--color-success) 12%, transparent);
    color: var(--color-success);
  }

  &--group {
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }
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
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
  margin-top: 8px;
}

.advanced-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 32px;

  &--tags {
    align-items: flex-start;
  }
}

.advanced-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  line-height: 32px;
}

.advanced-control {
  display: flex;
  justify-content: flex-end;

  :deep(.n-dynamic-tags) {
    justify-content: flex-end;
    min-height: 32px;

    .n-tag {
      height: 28px;
      margin: 2px 0 2px 6px !important;
    }

    .n-button {
      height: 28px;
    }
  }
}

.offset-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  height: 32px;
}

.offset-input {
  width: 70px;
  height: 32px;
  text-align: center;
}

.detect-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  height: 32px;
  padding: 0 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--transition-fast);

  &:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  &:disabled {
    cursor: wait;
  }
}

// Expand transition
.expand-enter-active,
.expand-leave-active {
  transition: all var(--transition-normal);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}

// Footer
.confirm-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}

.btn {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  font-family: inherit;
  font-weight: 500;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &-secondary {
    background: var(--color-surface-hover);
    border: 1px solid var(--color-border);
    color: var(--color-text);

    &:hover {
      background: var(--color-surface);
      border-color: var(--color-text-muted);
    }
  }

  &-primary {
    background: var(--color-primary);
    border: 1px solid var(--color-primary);
    color: #fff;

    &:hover {
      background: var(--color-primary-hover);
      border-color: var(--color-primary-hover);
    }
  }
}
</style>
