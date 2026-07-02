<script lang="ts" setup>
import { Close } from '@icon-park/vue-next';
import { NButton, NSpin, useMessage } from 'naive-ui';
import type { BangumiRule, DetectOffsetResponse } from '#/bangumi';

const emit = defineEmits<{
  (e: 'apply', rule: BangumiRule): void;
  (e: 'enable', id: number): void;
  (e: 'archive', id: number): void;
  (e: 'unarchive', id: number): void;
  (
    e: 'deleteFile',
    type: 'disable' | 'delete',
    opts: { id: number; deleteFile: boolean }
  ): void;
}>();

const { t } = useMyI18n();

const show = defineModel('show', { default: false });
const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const message = useMessage();

// Local deep copy for editing (prevents mutation of original)
const localRule = ref<BangumiRule>(JSON.parse(JSON.stringify(rule.value)));

// Sync when rule changes (e.g., opening different item)
watch(
  rule,
  (newVal) => {
    localRule.value = JSON.parse(JSON.stringify(newVal));
  },
  { deep: true }
);

const { posterSrc, infoTags, showAdvanced, copied, copyRssLink } =
  useBangumiRuleForm(localRule);
const offsetLoading = ref(false);
const offsetReason = ref('');
const dismissingReview = ref(false);

// Delete file dialog state
const deleteFileDialog = reactive<{
  show: boolean;
  type: 'disable' | 'delete';
}>({
  show: false,
  type: 'disable',
});

watch(show, (val) => {
  if (!val) {
    deleteFileDialog.show = false;
    showAdvanced.value = false;
    offsetReason.value = '';
  }
});

const rssLink = computed(() => localRule.value.rss_link?.[0] || '');

// Auto detect offset using the new detectOffset API
async function autoDetectOffset() {
  if (!localRule.value.official_title || !localRule.value.season) return;
  offsetLoading.value = true;
  offsetReason.value = '';
  try {
    const result: DetectOffsetResponse = await apiBangumi.detectOffset({
      title: localRule.value.official_title,
      parsed_season: localRule.value.season,
      parsed_episode: 1,
    });

    if (result.has_mismatch && result.suggestion) {
      localRule.value.season_offset = result.suggestion.season_offset;
      localRule.value.episode_offset = result.suggestion.episode_offset;
      offsetReason.value = result.suggestion.reason;
      // Clear needs_review after applying offset
      localRule.value.needs_review = false;
      localRule.value.needs_review_reason = null;
      message.success(t('offset.suggestion_applied'));
    } else {
      offsetReason.value = t('offset.no_mismatch');
      // Clear needs_review if no mismatch detected
      localRule.value.needs_review = false;
      localRule.value.needs_review_reason = null;
      message.info(t('offset.no_mismatch'));
    }
  } catch (e) {
    console.error('Failed to detect offset:', e);
    message.error(t('offset.detect_failed'));
  } finally {
    offsetLoading.value = false;
  }
}

// Dismiss the needs_review warning
async function dismissReview() {
  if (!localRule.value.id) return;
  dismissingReview.value = true;
  try {
    await apiBangumi.dismissReview(localRule.value.id);
    localRule.value.needs_review = false;
    localRule.value.needs_review_reason = null;
    message.success(t('offset.review_dismissed'));
  } catch (e) {
    console.error('Failed to dismiss review:', e);
    message.error(t('offset.dismiss_failed'));
  } finally {
    dismissingReview.value = false;
  }
}

const close = () => (show.value = false);

function showDeleteFileDialog() {
  deleteFileDialog.show = true;
  deleteFileDialog.type = 'delete';
}

function emitDeleteFile(deleteFile: boolean) {
  emit('deleteFile', deleteFileDialog.type, {
    id: rule.value.id,
    deleteFile,
  });
}

function emitApply() {
  // Copy local changes back to rule before emitting
  Object.assign(rule.value, localRule.value);
  emit('apply', rule.value);
}

function emitEnable() {
  emit('enable', rule.value.id);
}

function emitArchive() {
  emit('archive', rule.value.id);
}

function emitUnarchive() {
  emit('unarchive', rule.value.id);
}
</script>

<template>
  <!-- Enable deleted rule dialog -->
  <ab-popup
    v-if="rule.deleted"
    v-model:show="show"
    :title="$t('homepage.rule.enable_rule')"
    css="w-300 max-w-[90vw]"
  >
    <div>{{ $t('homepage.rule.enable_hit') }}</div>
    <div line my-8></div>
    <div f-cer gap-x-10>
      <NButton size="small" type="error" @click="emitEnable">
        {{ $t('homepage.rule.yes_btn') }}
      </NButton>
      <NButton type="primary" size="small" @click="close">
        {{ $t('homepage.rule.no_btn') }}
      </NButton>
    </div>
  </ab-popup>

  <!-- Main edit modal -->
  <Teleport v-else to="body">
    <Transition name="modal">
      <div v-if="show" class="edit-backdrop" @click.self="close">
        <div class="edit-modal" role="dialog" aria-modal="true">
          <!-- Header -->
          <header class="edit-header">
            <h2 class="edit-title">{{ $t('homepage.rule.edit_rule') }}</h2>
            <button class="close-btn" aria-label="Close" @click="close">
              <Close theme="outline" size="18" />
            </button>
          </header>

          <!-- Needs Review Warning Banner -->
          <div v-if="localRule.needs_review" class="review-warning">
            <div class="review-warning-main">
              <span class="review-warning-emoji">⚠️</span>
              <div class="review-warning-content">
                <div class="review-warning-title">
                  {{ $t('offset.needs_review') }}
                </div>
                <div
                  v-if="localRule.needs_review_reason"
                  class="review-warning-reason"
                >
                  {{ localRule.needs_review_reason }}
                </div>
              </div>
            </div>
            <div class="review-warning-actions">
              <button
                class="detect-btn"
                :disabled="offsetLoading"
                @click="autoDetectOffset"
              >
                <NSpin v-if="offsetLoading" :size="12" />
                <span v-else>{{ $t('homepage.rule.auto_detect') }}</span>
              </button>
              <button
                class="dismiss-btn"
                :disabled="dismissingReview"
                @click="dismissReview"
              >
                <NSpin v-if="dismissingReview" :size="12" />
                <span v-else>{{ $t('offset.dismiss') }}</span>
              </button>
            </div>
          </div>

          <!-- Content -->
          <div class="edit-content">
            <bangumi-preview v-model:rule="localRule" :poster-src="posterSrc" />

            <bangumi-info-tags :tags="infoTags" />

            <bangumi-rss-link-row
              :link="rssLink"
              :copied="copied"
              @copy="copyRssLink(rssLink)"
            />

            <!-- Advanced settings -->
            <advanced-section v-model:open="showAdvanced">
              <bangumi-filter-field v-model="localRule.filter" />

              <bangumi-offset-field
                v-model="localRule.season_offset"
                :label="$t('homepage.rule.season_offset')"
              />

              <bangumi-offset-field
                v-model="localRule.episode_offset"
                :label="$t('homepage.rule.episode_offset')"
              />
            </advanced-section>
          </div>

          <!-- Footer -->
          <footer class="edit-footer">
            <div class="footer-left">
              <NButton
                v-if="localRule.archived"
                type="primary"
                size="small"
                @click="emitUnarchive"
              >
                {{ $t('homepage.rule.unarchive') }}
              </NButton>
              <NButton v-else type="primary" size="small" @click="emitArchive">
                {{ $t('homepage.rule.archive') }}
              </NButton>
              <NButton size="small" type="error" @click="showDeleteFileDialog">
                {{ $t('homepage.rule.delete') }}
              </NButton>
            </div>
            <div class="footer-right">
              <NButton type="primary" size="small" @click="emitApply">
                {{ $t('homepage.rule.apply') }}
              </NButton>
            </div>
          </footer>
        </div>

        <!-- Delete confirmation dialog -->
        <Transition name="modal">
          <div
            v-if="deleteFileDialog.show"
            class="delete-dialog-backdrop"
            @click.self="deleteFileDialog.show = false"
          >
            <div class="delete-dialog">
              <h3 class="delete-title">{{ $t('homepage.rule.delete') }}</h3>
              <p class="delete-message">{{ $t('homepage.rule.delete_hit') }}</p>
              <div class="delete-actions">
                <NButton
                  size="small"
                  type="primary"
                  secondary
                  @click="emitDeleteFile(false)"
                >
                  {{ $t('homepage.rule.no_btn') }}
                </NButton>
                <NButton
                  size="small"
                  type="error"
                  @click="emitDeleteFile(true)"
                >
                  {{ $t('homepage.rule.yes_btn') }}
                </NButton>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
.edit-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay);
  z-index: var(--z-modal);
  padding: 16px;
}

.edit-modal {
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

.edit-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.edit-title {
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

// Review warning banner
.review-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  margin: 12px 20px;
  background: #fef9ed;
  border: 1px solid #fde68a;
  border-radius: var(--radius-md);
}

.review-warning-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.review-warning-emoji {
  font-size: 20px;
  flex-shrink: 0;
}

.review-warning-content {
  flex: 1;
  min-width: 0;
}

.review-warning-title {
  font-size: 13px;
  font-weight: 600;
  color: #92400e;
}

.review-warning-reason {
  font-size: 12px;
  color: #a16207;
  line-height: 1.3;
  margin-top: 2px;
}

.review-warning-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.review-warning-actions .detect-btn,
.review-warning-actions .dismiss-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  padding: 0 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);

  &:disabled {
    cursor: wait;
  }
}

.review-warning-actions .detect-btn {
  min-width: 90px;
  color: #fff;
  background: var(--color-primary);
  border: none;

  &:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }
}

.review-warning-actions .dismiss-btn {
  min-width: 70px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);

  &:hover:not(:disabled) {
    border-color: var(--color-text-muted);
    color: var(--color-text);
  }
}

.edit-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

// Footer
.edit-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
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

// Delete confirmation dialog
.delete-dialog-backdrop {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay);
  z-index: calc(var(--z-modal) + 10);
}

.delete-dialog {
  width: 100%;
  max-width: 320px;
  padding: 24px;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
}

.delete-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 12px;
}

.delete-message {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 20px;
}

.delete-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

// Modal transition
.modal-enter-active,
.modal-leave-active {
  transition: opacity 200ms ease;

  .edit-modal,
  .delete-dialog {
    transition: transform 200ms ease, opacity 200ms ease;
  }
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .edit-modal,
  .delete-dialog {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
}

// Responsive adjustments
@media (max-width: 480px) {
  .edit-footer {
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
