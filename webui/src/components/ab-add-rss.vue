<script lang="ts" setup>
import { CheckOne, Close, Copy, Down, ErrorPicture, Link, Right } from '@icon-park/vue-next';
import { NDynamicTags, NSpin } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';
import type { RSS } from '#/rss';
import { rssTemplate } from '#/rss';
import { ruleTemplate } from '#/bangumi';

/** v-model show */
const show = defineModel('show', { default: false });

const message = useMessage();
const { getAll } = useBangumiStore();
const { t } = useMyI18n();

const rss = ref<RSS>({ ...rssTemplate });
const rule = defineModel<BangumiRule>('rule', { default: () => ({ ...ruleTemplate }) });
const parserTypes = ['tmdb', 'mikan', 'parser'] as const;

// UI state
const step = ref<'input' | 'confirm'>('input');
const showAdvanced = ref(true);
const copied = ref(false);
const offsetLoading = ref(false);
const offsetReason = ref('');

const loading = reactive({
  analyze: false,
  collect: false,
  subscribe: false,
});

// Computed
const posterSrc = computed(() => resolvePosterUrl(rule.value.poster_link));

const infoTags = computed(() => {
  const tags: { value: string; type: string }[] = [];
  const { season, season_raw, dpi, subtitle, group_name } = rule.value;

  if (season || season_raw) {
    const seasonDisplay = season_raw || (season ? `S${season}` : '');
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

// Watchers
watch(show, (val) => {
  if (!val) {
    // Reset state when closing
    rss.value = { ...rssTemplate };
    step.value = 'input';
    offsetReason.value = '';
  } else if (val && rule.value.official_title !== '') {
    // If rule already has data, go to confirm step
    step.value = 'confirm';
  }
});

// Methods
function close() {
  show.value = false;
}

function addRss() {
  if (rss.value.url === '') {
    message.error(t('notify.please_enter', [t('notify.rss_link')]));
    return;
  }

  if (rss.value.aggregate) {
    // Aggregate mode: directly add RSS
    useApi(apiRSS.add, {
      showMessage: true,
      onBeforeExecute() {
        loading.analyze = true;
      },
      onSuccess() {
        show.value = false;
      },
      onFinally() {
        loading.analyze = false;
      },
    }).execute(rss.value);
  } else {
    // Single mode: analyze and show confirm
    useApi(apiDownload.analysis, {
      showMessage: true,
      onBeforeExecute() {
        loading.analyze = true;
      },
      onSuccess(res) {
        rule.value = res;
        step.value = 'confirm';
      },
      onFinally() {
        loading.analyze = false;
      },
    }).execute(rss.value);
  }
}

function goBack() {
  step.value = 'input';
}

async function copyRssLink() {
  const rssLink = rule.value.rss_link?.[0] || rss.value.url || '';
  if (rssLink) {
    await navigator.clipboard.writeText(rssLink);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  }
}

async function autoDetectOffset() {
  if (!rule.value.id) return;
  offsetLoading.value = true;
  offsetReason.value = '';
  try {
    const result = await apiBangumi.suggestOffset(rule.value.id);
    rule.value.episode_offset = result.suggested_offset;
    offsetReason.value = result.reason;
  } catch (e) {
    console.error('Failed to detect offset:', e);
    message.error('Failed to detect offset');
  } finally {
    offsetLoading.value = false;
  }
}

function collect() {
  if (!rule.value) return;
  useApi(apiDownload.collection, {
    showMessage: true,
    onBeforeExecute() {
      loading.collect = true;
    },
    onSuccess() {
      getAll();
      show.value = false;
    },
    onFinally() {
      loading.collect = false;
    },
  }).execute(rule.value);
}

function subscribe() {
  if (!rule.value) return;
  useApi(apiDownload.subscribe, {
    showMessage: true,
    onBeforeExecute() {
      loading.subscribe = true;
    },
    onSuccess() {
      getAll();
      show.value = false;
    },
    onFinally() {
      loading.subscribe = false;
    },
  }).execute(rule.value, rss.value);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" class="add-backdrop" @click.self="close">
        <div class="add-modal" role="dialog" aria-modal="true">
          <!-- Header -->
          <header class="add-header">
            <h2 class="add-title">{{ $t('topbar.add.title') }}</h2>
            <button class="close-btn" aria-label="Close" @click="close">
              <Close theme="outline" size="18" />
            </button>
          </header>

          <!-- Step 1: Input RSS -->
          <div v-if="step === 'input'" class="add-content">
            <div class="form-section">
              <!-- RSS Link -->
              <div class="form-group">
                <label class="form-label">{{ $t('topbar.add.rss_link') }}</label>
                <div class="input-wrapper">
                  <Link theme="outline" size="16" class="input-icon" />
                  <input
                    v-model="rss.url"
                    type="text"
                    class="form-input form-input--with-icon"
                    :placeholder="$t('topbar.add.placeholder_link')"
                  />
                </div>
              </div>

              <!-- Name -->
              <div class="form-group">
                <label class="form-label">{{ $t('topbar.add.name') }}</label>
                <input
                  v-model="rss.name"
                  type="text"
                  class="form-input"
                  :placeholder="$t('topbar.add.placeholder_name')"
                />
              </div>

              <!-- Options row -->
              <div class="options-row">
                <!-- Aggregate Switch -->
                <div class="option-item">
                  <label class="option-label">{{ $t('topbar.add.aggregate') }}</label>
                  <label class="switch">
                    <input v-model="rss.aggregate" type="checkbox" />
                    <span class="switch-slider"></span>
                  </label>
                </div>

                <!-- Parser Select -->
                <div class="option-item">
                  <label class="option-label">{{ $t('topbar.add.parser') }}</label>
                  <select v-model="rss.parser" class="form-select">
                    <option v-for="type in parserTypes" :key="type" :value="type">
                      {{ type }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <footer class="add-footer">
              <ab-button size="small" :loading="loading.analyze" @click="addRss">
                {{ $t('topbar.add.button') }}
              </ab-button>
            </footer>
          </div>

          <!-- Step 2: Confirm -->
          <template v-else>
            <div class="add-content">
              <!-- Bangumi Info -->
              <div class="bangumi-info">
                <div class="bangumi-poster">
                  <template v-if="rule.poster_link">
                    <img :src="posterSrc" :alt="rule.official_title" />
                  </template>
                  <template v-else>
                    <div class="poster-placeholder">
                      <ErrorPicture theme="outline" size="32" />
                    </div>
                  </template>
                </div>
                <div class="bangumi-meta">
                  <input
                    v-model="rule.official_title"
                    type="text"
                    class="title-input"
                    :placeholder="$t('homepage.rule.official_title')"
                  />
                  <p v-if="rule.title_raw" class="bangumi-subtitle">{{ rule.title_raw }}</p>
                  <div class="meta-row">
                    <input
                      :value="rule.year ?? ''"
                      type="text"
                      class="year-input"
                      :class="{ 'year-input--empty': !rule.year }"
                      :placeholder="$t('homepage.rule.year')"
                      @input="(e) => rule.year = (e.target as HTMLInputElement).value || null"
                    />
                    <span class="meta-separator">·</span>
                    <label class="season-label">S</label>
                    <input
                      v-model.number="rule.season"
                      type="number"
                      class="season-input"
                      min="1"
                    />
                  </div>
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

              <!-- RSS Link Display -->
              <div v-if="rule.rss_link?.[0] || rss.url" class="rss-section">
                <div class="info-row">
                  <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
                  <span class="info-value info-value--link">
                    {{ rule.rss_link?.[0] || rss.url || '-' }}
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

                <Transition name="expand">
                  <div v-show="showAdvanced" class="advanced-content">
                    <!-- Filter rules row -->
                    <div class="advanced-row advanced-row--tags">
                      <label class="advanced-label">{{ $t('homepage.rule.filter') }}</label>
                      <div class="advanced-control filter-tags">
                        <NDynamicTags v-model:value="rule.filter" size="small" />
                      </div>
                    </div>

                    <!-- Offset row -->
                    <div class="advanced-row">
                      <label class="advanced-label">{{ $t('homepage.rule.offset') }}</label>
                      <div class="advanced-control offset-controls">
                        <input
                          v-model.number="rule.episode_offset"
                          type="number"
                          ab-input
                          class="offset-input"
                        />
                        <button
                          class="detect-btn"
                          :disabled="offsetLoading || !rule.id"
                          @click="autoDetectOffset"
                        >
                          <NSpin v-if="offsetLoading" :size="14" />
                          <span v-else>{{ $t('homepage.rule.auto_detect') }}</span>
                        </button>
                      </div>
                    </div>
                    <div v-if="offsetReason" class="offset-reason">{{ offsetReason }}</div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- Footer -->
            <footer class="add-footer add-footer--confirm">
              <div class="footer-left">
                <ab-button size="small" type="secondary" @click="goBack">
                  {{ $t('setup.nav.previous') }}
                </ab-button>
              </div>
              <div class="footer-right">
                <ab-button size="small" :loading="loading.collect" @click="collect">
                  {{ $t('topbar.add.collect') }}
                </ab-button>
                <ab-button size="small" :loading="loading.subscribe" @click="subscribe">
                  {{ $t('topbar.add.subscribe') }}
                </ab-button>
              </div>
            </footer>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
.add-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay);
  z-index: var(--z-modal);
  padding: 16px;
}

.add-modal {
  width: 100%;
  max-width: 480px;
  max-height: 90dvh; // Use dynamic viewport height for iOS Safari keyboard support
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;

  // Fallback for browsers that don't support dvh
  @supports not (max-height: 1dvh) {
    max-height: 90vh;
  }
}

.add-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.add-title {
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

.add-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

// Form Section (Step 1)
.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 12px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 15%, transparent);
  }

  &::placeholder {
    color: var(--color-text-muted);
  }

  &--with-icon {
    padding-left: 40px;
  }
}

.form-select {
  height: 36px;
  padding: 0 32px 0 12px;
  font-size: 13px;
  font-family: inherit;
  color: var(--color-text);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6,9 12,15 18,9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  transition: border-color var(--transition-fast);

  &:focus {
    border-color: var(--color-primary);
  }
}

.options-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--color-surface-hover);
  border-radius: var(--radius-md);
}

.option-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.option-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

// Custom Switch
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;

  input {
    opacity: 0;
    width: 0;
    height: 0;
  }
}

.switch-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: var(--color-border);
  border-radius: 24px;
  transition: background-color var(--transition-fast);

  &::before {
    content: '';
    position: absolute;
    left: 2px;
    bottom: 2px;
    width: 20px;
    height: 20px;
    background: #fff;
    border-radius: 50%;
    transition: transform var(--transition-fast);
  }

  input:checked + & {
    background: var(--color-primary);
  }

  input:checked + &::before {
    transform: translateX(20px);
  }
}

// Footer
.add-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);

  &--confirm {
    justify-content: space-between;
  }
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

// Bangumi Info (Step 2 - same as ab-edit-rule)
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
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-input {
  width: 100%;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 4px 0;
  outline: none;
  transition: border-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::placeholder {
    color: var(--color-text-muted);
    font-weight: 400;
  }
}

.bangumi-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.year-input {
  width: 60px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  outline: none;
  transition: border-color var(--transition-fast), background-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::placeholder {
    color: var(--color-text-muted);
  }

  &--empty {
    background: color-mix(in srgb, var(--color-warning) 15%, transparent);
    border-bottom-color: var(--color-warning);
    border-radius: var(--radius-xs) var(--radius-xs) 0 0;
    padding: 2px 4px;

    &::placeholder {
      color: var(--color-warning);
    }
  }
}

.meta-separator {
  color: var(--color-text-muted);
}

.season-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.season-input {
  width: 40px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  outline: none;
  text-align: center;
  transition: border-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  -moz-appearance: textfield;
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
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.offset-reason {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: -4px;
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

// Modal transition
.modal-enter-active,
.modal-leave-active {
  transition: opacity 200ms ease;

  .add-modal {
    transition: transform 200ms ease, opacity 200ms ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .add-modal {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
}

// Responsive
@media (max-width: 480px) {
  .options-row {
    flex-direction: column;
    gap: 16px;
  }

  .option-item {
    justify-content: space-between;
    width: 100%;
  }

  .add-footer--confirm {
    flex-direction: column;
    gap: 12px;
  }

  .footer-left,
  .footer-right {
    width: 100%;
    justify-content: center;
  }

  .footer-right {
    order: -1;
  }
}
</style>
