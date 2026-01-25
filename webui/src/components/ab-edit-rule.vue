<script lang="ts" setup>
import { CheckOne, Close, Copy, Down, ErrorPicture, Right } from '@icon-park/vue-next';
import { NDynamicTags, NSpin, useMessage } from 'naive-ui';
import type { BangumiRule } from '#/bangumi';

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
watch(rule, (newVal) => {
  localRule.value = JSON.parse(JSON.stringify(newVal));
}, { deep: true });

const posterSrc = computed(() => resolvePosterUrl(localRule.value.poster_link));
const showAdvanced = ref(true);
const copied = ref(false);
const offsetLoading = ref(false);
const offsetReason = ref('');

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

// Info tags for display
const infoTags = computed(() => {
  const tags: { value: string; type: string }[] = [];
  const { season, season_raw, dpi, subtitle, group_name } = localRule.value;

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

// Copy RSS link
async function copyRssLink() {
  const rssLink = localRule.value.rss_link?.[0] || '';
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
  if (!localRule.value.id) return;
  offsetLoading.value = true;
  offsetReason.value = '';
  try {
    const result = await apiBangumi.suggestOffset(localRule.value.id);
    localRule.value.offset = result.suggested_offset;
    offsetReason.value = result.reason;
  } catch (e) {
    console.error('Failed to detect offset:', e);
    message.error('Failed to detect offset');
  } finally {
    offsetLoading.value = false;
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
      <ab-button size="small" type="warn" @click="emitEnable">
        {{ $t('homepage.rule.yes_btn') }}
      </ab-button>
      <ab-button size="small" @click="close">
        {{ $t('homepage.rule.no_btn') }}
      </ab-button>
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

          <!-- Content -->
          <div class="edit-content">
            <!-- Bangumi Info -->
            <div class="bangumi-info">
              <div class="bangumi-poster">
                <template v-if="localRule.poster_link">
                  <img :src="posterSrc" :alt="localRule.official_title" />
                </template>
                <template v-else>
                  <div class="poster-placeholder">
                    <ErrorPicture theme="outline" size="32" />
                  </div>
                </template>
              </div>
              <div class="bangumi-meta">
                <input
                  v-model="localRule.official_title"
                  type="text"
                  class="title-input"
                  :placeholder="$t('homepage.rule.official_title')"
                />
                <p v-if="localRule.title_raw" class="bangumi-subtitle">{{ localRule.title_raw }}</p>
                <div class="meta-row">
                  <input
                    :value="localRule.year ?? ''"
                    type="text"
                    class="year-input"
                    :class="{ 'year-input--empty': !localRule.year }"
                    :placeholder="$t('homepage.rule.year')"
                    @input="(e) => localRule.year = (e.target as HTMLInputElement).value || null"
                  />
                  <span class="meta-separator">·</span>
                  <label class="season-label">S</label>
                  <input
                    v-model.number="localRule.season"
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

            <!-- RSS Link -->
            <div v-if="localRule.rss_link?.[0]" class="rss-section">
              <div class="info-row">
                <span class="info-label">{{ $t('search.confirm.rss') }}:</span>
                <span class="info-value info-value--link">
                  {{ localRule.rss_link?.[0] || '-' }}
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
                      <NDynamicTags v-model:value="localRule.filter" size="small" />
                    </div>
                  </div>

                  <!-- Offset row -->
                  <div class="advanced-row">
                    <label class="advanced-label">{{ $t('homepage.rule.offset') }}</label>
                    <div class="advanced-control offset-controls">
                      <input
                        v-model.number="localRule.offset"
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
                  <div v-if="offsetReason" class="offset-reason">{{ offsetReason }}</div>
                </div>
              </Transition>
            </div>
          </div>

          <!-- Footer -->
          <footer class="edit-footer">
            <div class="footer-left">
              <ab-button
                v-if="localRule.archived"
                size="small"
                @click="emitUnarchive"
              >
                {{ $t('homepage.rule.unarchive') }}
              </ab-button>
              <ab-button
                v-else
                size="small"
                @click="emitArchive"
              >
                {{ $t('homepage.rule.archive') }}
              </ab-button>
              <ab-button
                size="small"
                type="warn"
                @click="showDeleteFileDialog"
              >
                {{ $t('homepage.rule.delete') }}
              </ab-button>
            </div>
            <div class="footer-right">
              <ab-button size="small" @click="emitApply">
                {{ $t('homepage.rule.apply') }}
              </ab-button>
            </div>
          </footer>
        </div>

        <!-- Delete confirmation dialog -->
        <Transition name="modal">
          <div v-if="deleteFileDialog.show" class="delete-dialog-backdrop" @click.self="deleteFileDialog.show = false">
            <div class="delete-dialog">
              <h3 class="delete-title">{{ $t('homepage.rule.delete') }}</h3>
              <p class="delete-message">{{ $t('homepage.rule.delete_hit') }}</p>
              <div class="delete-actions">
                <ab-button size="small" type="secondary" @click="emitDeleteFile(false)">
                  {{ $t('homepage.rule.no_btn') }}
                </ab-button>
                <ab-button size="small" type="warn" @click="emitDeleteFile(true)">
                  {{ $t('homepage.rule.yes_btn') }}
                </ab-button>
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

.edit-content {
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

  // Hide spinner buttons
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
    cursor: wait;
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
