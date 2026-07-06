<script lang="ts" setup>
import { Close, Link } from '@icon-park/vue-next';
import { NSelect, NSpin, NSwitch } from 'naive-ui';
import { onKeyStroke } from '@vueuse/core';
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
const rule = defineModel<BangumiRule>('rule', {
  default: () => ({ ...ruleTemplate }),
});
const parserTypes = ['tmdb', 'mikan', 'parser'] as const;

// UI state
const step = ref<'input' | 'confirm'>('input');
const offsetLoading = ref(false);
const offsetReason = ref('');

const { posterSrc, infoTags, showAdvanced, copied, copyRssLink } =
  useBangumiRuleForm(rule);

const loading = reactive({
  analyze: false,
  collect: false,
  subscribe: false,
});

const { execute: addRssAggregate } = useApi(apiRSS.add, {
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
});

const { execute: analyzeRss } = useApi(apiDownload.analysis, {
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
});

const { execute: executeCollect } = useApi(apiDownload.collection, {
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
});

const { execute: executeSubscribe } = useApi(apiDownload.subscribe, {
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

onKeyStroke('Escape', () => {
  if (show.value) close();
});

function addRss() {
  if (rss.value.url === '') {
    message.error(t('notify.please_enter', [t('notify.rss_link')]));
    return;
  }

  if (rss.value.aggregate) {
    addRssAggregate(rss.value);
  } else {
    analyzeRss(rss.value);
  }
}

function goBack() {
  step.value = 'input';
}

const rssLink = computed(() => rule.value.rss_link?.[0] || rss.value.url || '');

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
    message.error(t('offset.detect_failed'));
  } finally {
    offsetLoading.value = false;
  }
}

function collect() {
  if (!rule.value) return;
  executeCollect(rule.value);
}

function subscribe() {
  if (!rule.value) return;
  executeSubscribe(rule.value, rss.value);
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
                <label class="form-label">{{
                  $t('topbar.add.rss_link')
                }}</label>
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
                  <label class="option-label">{{
                    $t('topbar.add.aggregate')
                  }}</label>
                  <NSwitch v-model:value="rss.aggregate" />
                </div>

                <!-- Parser Select -->
                <div class="option-item">
                  <label class="option-label">{{
                    $t('topbar.add.parser')
                  }}</label>
                  <NSelect
                    v-model:value="rss.parser"
                    :options="parserTypes.map((p) => ({ label: p, value: p }))"
                    class="parser-select"
                  />
                </div>
              </div>
            </div>

            <!-- Footer -->
            <footer class="add-footer">
              <ab-button
                variant="primary"
                size="sm"
                :loading="loading.analyze"
                @click="addRss"
              >
                {{ $t('topbar.add.button') }}
              </ab-button>
            </footer>
          </div>

          <!-- Step 2: Confirm -->
          <template v-else>
            <div class="add-content">
              <bangumi-preview v-model:rule="rule" :poster-src="posterSrc" />

              <bangumi-info-tags :tags="infoTags" />

              <bangumi-rss-link-row
                :link="rssLink"
                :copied="copied"
                @copy="copyRssLink(rssLink)"
              />

              <!-- Advanced settings -->
              <advanced-section v-model:open="showAdvanced">
                <bangumi-filter-field v-model="rule.filter" />

                <bangumi-offset-field
                  v-model="rule.episode_offset"
                  :label="$t('homepage.rule.offset')"
                >
                  <template #action>
                    <button
                      class="detect-btn"
                      :disabled="offsetLoading || !rule.id"
                      @click="autoDetectOffset"
                    >
                      <NSpin v-if="offsetLoading" :size="14" />
                      <span v-else>{{ $t('homepage.rule.auto_detect') }}</span>
                    </button>
                  </template>
                </bangumi-offset-field>
                <div v-if="offsetReason" class="offset-reason">
                  {{ offsetReason }}
                </div>
              </advanced-section>
            </div>

            <!-- Footer -->
            <footer class="add-footer add-footer--confirm">
              <div class="footer-left">
                <ab-button variant="secondary" size="sm" @click="goBack">
                  {{ $t('setup.nav.previous') }}
                </ab-button>
              </div>
              <div class="footer-right">
                <ab-button
                  variant="primary"
                  size="sm"
                  :loading="loading.collect"
                  @click="collect"
                >
                  {{ $t('topbar.add.collect') }}
                </ab-button>
                <ab-button
                  variant="primary"
                  size="sm"
                  :loading="loading.subscribe"
                  @click="subscribe"
                >
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

  @include forTouch {
    width: var(--touch-target);
    height: var(--touch-target);
  }
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
  transition: border-color var(--transition-fast),
    box-shadow var(--transition-fast);

  &:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px
      color-mix(in srgb, var(--color-primary) 15%, transparent);
  }

  &::placeholder {
    color: var(--color-text-muted);
  }

  &--with-icon {
    padding-left: 40px;
  }
}

.parser-select {
  width: 140px;
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

// Offset detect button + reason (specific to the add-rss flow;
// shared preview/tags/rss-link/filter/offset-row styles live in the
// bangumi-* / advanced-section sub-components)
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
