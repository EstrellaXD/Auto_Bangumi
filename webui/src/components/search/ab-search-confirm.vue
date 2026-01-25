<script lang="ts" setup>
import { CheckOne, Close, Copy, Down, ErrorPicture, Right } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

const props = defineProps<{
  bangumi: BangumiRule;
}>();

const emit = defineEmits<{
  (e: 'confirm', bangumi: BangumiRule): void;
  (e: 'cancel'): void;
}>();

const posterSrc = computed(() => resolvePosterUrl(props.bangumi.poster_link));
const showAdvanced = ref(false);
const copied = ref(false);

// Format season display
const seasonDisplay = computed(() => {
  if (props.bangumi.season_raw) {
    return props.bangumi.season_raw;
  }
  return props.bangumi.season ? `Season ${props.bangumi.season}` : '';
});

// Copy RSS link
async function copyRssLink() {
  const rssLink = props.bangumi.rss_link?.[0] || '';
  if (rssLink) {
    await navigator.clipboard.writeText(rssLink);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  }
}

function handleConfirm() {
  emit('confirm', props.bangumi);
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
            <template v-if="bangumi.poster_link">
              <img :src="posterSrc" :alt="bangumi.official_title" />
            </template>
            <template v-else>
              <div class="poster-placeholder">
                <ErrorPicture theme="outline" size="32" />
              </div>
            </template>
          </div>
          <div class="bangumi-meta">
            <h3 class="bangumi-title">{{ bangumi.official_title }}</h3>
            <p v-if="bangumi.title_raw" class="bangumi-subtitle">{{ bangumi.title_raw }}</p>
            <div class="bangumi-details">
              <span v-if="bangumi.year">{{ bangumi.year }}</span>
              <span v-if="seasonDisplay">{{ seasonDisplay }}</span>
            </div>
          </div>
        </div>

        <!-- Info rows -->
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
            <span class="info-value info-value--link">
              {{ bangumi.rss_link?.[0] || '-' }}
            </span>
            <button class="copy-btn" :class="{ copied }" @click="copyRssLink">
              <CheckOne v-if="copied" theme="outline" size="14" />
              <Copy v-else theme="outline" size="14" />
            </button>
          </div>

          <div class="info-row">
            <span class="info-label">{{ $t('search.confirm.group') }}:</span>
            <span class="info-value">{{ bangumi.group_name || '-' }}</span>
          </div>

          <div class="info-row">
            <span class="info-label">{{ $t('search.confirm.resolution') }}:</span>
            <span class="info-value">{{ bangumi.dpi || '-' }}</span>
          </div>

          <div class="info-row">
            <span class="info-label">{{ $t('search.confirm.subtitle') }}:</span>
            <span class="info-value">{{ bangumi.subtitle || '-' }}</span>
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
              <div class="info-row">
                <span class="info-label">{{ $t('search.confirm.filter') }}:</span>
                <span class="info-value info-value--code">
                  {{ bangumi.filter?.join(', ') || '-' }}
                </span>
              </div>

              <div class="info-row">
                <span class="info-label">{{ $t('search.confirm.save_path') }}:</span>
                <span class="info-value info-value--code">
                  {{ bangumi.save_path || '-' }}
                </span>
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

.bangumi-details {
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);

  span {
    &:not(:last-child)::after {
      content: '·';
      margin-left: 8px;
      color: var(--color-text-muted);
    }
  }
}

// Info section
.info-section {
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

  &--code {
    font-family: 'Fira Code', monospace;
    font-size: 12px;
    background: var(--color-surface);
    padding: 4px 8px;
    border-radius: var(--radius-sm);
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
