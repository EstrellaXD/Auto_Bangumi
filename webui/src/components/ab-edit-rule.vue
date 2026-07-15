<script lang="ts" setup>
import { More } from '@icon-park/vue-next';
import { NCheckbox, NSelect, NSpin, useMessage } from 'naive-ui';
import { onKeyStroke } from '@vueuse/core';
import type { BangumiRule, DetectOffsetResponse } from '#/bangumi';
import type { AbMenuItem } from '@/components/basic/ab-menu.vue';

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
const { isMobile } = useBreakpointQuery();

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
const deleteLocalFiles = ref(false);
const mobileActionsRef = ref<HTMLElement | null>(null);
const mobileDeleteActive = computed(
  () => isMobile.value && deleteFileDialog.show
);

function returnToEditor() {
  deleteFileDialog.show = false;
  nextTick(() => {
    window.setTimeout(() => {
      mobileActionsRef.value
        ?.querySelector<HTMLButtonElement>('button')
        ?.focus();
    });
  });
}

const editorModalShow = computed({
  get: () => show.value,
  set: (value: boolean) => {
    if (!value && mobileDeleteActive.value) {
      returnToEditor();
      return;
    }
    show.value = value;
  },
});

watch(show, (val) => {
  if (!val) {
    deleteFileDialog.show = false;
    showAdvanced.value = false;
    offsetReason.value = '';
  }
});

const rssLink = computed(() => localRule.value.rss_link?.[0] || '');

// Air-weekday select — the drag-to-assign board is desktop-pointer-only, so
// the editor must offer a mobile/keyboard path to the same field.
const WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;
const weekdayOptions = computed(() =>
  WEEKDAY_KEYS.map((key, index) => ({
    label: t(`calendar.days.${key}`),
    value: index,
  }))
);

function onWeekdayChange(value: number | null) {
  localRule.value.air_weekday = value;
  // Mirror the dedicated setWeekday endpoint: an explicit choice locks the
  // day against the automatic scanner; clearing unlocks it.
  localRule.value.weekday_locked = value !== null;
}

const episodeTypeOptions = computed(() => [
  { label: t('homepage.rule.type_episode'), value: 'episode' },
  { label: t('homepage.rule.type_movie'), value: 'movie' },
  { label: t('homepage.rule.type_special'), value: 'special' },
]);

// 常见分辨率作预设，filterable+tag 允许输入任意值
const resolutionOptions = ['2160p', '1080p', '720p'].map((r) => ({
  label: r,
  value: r,
}));

const selectMenuProps = { role: 'listbox' } as const;

function selectOptionNodeProps() {
  return { role: 'option' };
}

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

// 种子管理页入口：关闭弹窗后跳转到该规则的种子列表
const router = useRouter();

function goToTorrents() {
  close();
  router.push(`/bangumi-torrents/${rule.value.id}`);
}

onKeyStroke('Escape', () => {
  if (!show.value || isMobile.value) return;
  // Inner delete dialog closes first, then the modal itself.
  if (deleteFileDialog.show) {
    deleteFileDialog.show = false;
  } else {
    close();
  }
});

function showDeleteFileDialog() {
  deleteLocalFiles.value = false;
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

const mobileRuleActions = computed<AbMenuItem[]>(() => [
  {
    key: 'torrents',
    label: () => t('homepage.rule.view_torrents'),
    handler: goToTorrents,
  },
  {
    key: localRule.value.archived ? 'unarchive' : 'archive',
    label: () =>
      t(
        localRule.value.archived
          ? 'homepage.rule.unarchive'
          : 'homepage.rule.archive'
      ),
    handler: localRule.value.archived ? emitUnarchive : emitArchive,
  },
  {
    key: 'delete',
    label: () => t('homepage.rule.delete'),
    danger: true,
    handler: showDeleteFileDialog,
  },
]);
</script>

<template>
  <!-- Enable deleted rule dialog -->
  <ab-modal
    v-if="rule.deleted"
    v-model:show="show"
    size="sm"
    :title="$t('homepage.rule.enable_rule')"
  >
    <div>{{ $t('homepage.rule.enable_hit') }}</div>

    <template #footer>
      <ab-button size="sm" @click="close">
        {{ $t('homepage.rule.no_btn') }}
      </ab-button>
      <ab-button size="sm" variant="primary" @click="emitEnable">
        {{ $t('homepage.rule.yes_btn') }}
      </ab-button>
    </template>
  </ab-modal>

  <!-- Main edit modal -->
  <ab-modal
    v-else
    v-model:show="editorModalShow"
    :title="
      mobileDeleteActive
        ? $t('homepage.rule.delete')
        : $t('homepage.rule.edit_rule')
    "
    mobile-fullscreen
    :avoid-keyboard="false"
  >
    <template v-if="mobileDeleteActive">
      <p class="delete-message">
        {{ $t('homepage.rule.delete_confirm') }}
      </p>
      <NCheckbox v-model:checked="deleteLocalFiles" class="delete-files-option">
        {{ $t('homepage.rule.delete_files_label') }}
      </NCheckbox>
    </template>

    <!-- Needs Review Warning Banner -->
    <div
      v-if="!mobileDeleteActive && localRule.needs_review"
      class="review-warning"
      role="status"
      :aria-label="$t('offset.needs_review')"
    >
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
    <div v-if="!mobileDeleteActive" class="edit-content">
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

        <div class="weekday-row">
          <label class="weekday-label">{{
            $t('homepage.rule.air_weekday')
          }}</label>
          <NSelect
            :value="localRule.air_weekday ?? null"
            :options="weekdayOptions"
            role="combobox"
            aria-haspopup="listbox"
            :menu-props="selectMenuProps"
            :node-props="selectOptionNodeProps"
            clearable
            size="small"
            :placeholder="$t('calendar.unknown')"
            :aria-label="$t('homepage.rule.air_weekday')"
            class="weekday-select"
            @update:value="onWeekdayChange"
          />
        </div>

        <div class="weekday-row">
          <label class="weekday-label">{{
            $t('homepage.rule.episode_type')
          }}</label>
          <NSelect
            v-model:value="localRule.episode_type"
            :options="episodeTypeOptions"
            role="combobox"
            aria-haspopup="listbox"
            :menu-props="selectMenuProps"
            :node-props="selectOptionNodeProps"
            size="small"
            :aria-label="$t('homepage.rule.episode_type')"
            class="weekday-select"
          />
        </div>

        <div class="weekday-row">
          <label class="weekday-label">{{
            $t('homepage.rule.preferred_group')
          }}</label>
          <ab-input
            :model-value="localRule.preferred_group ?? ''"
            type="text"
            class="preferred-input"
            placeholder="ANi"
            :aria-label="$t('homepage.rule.preferred_group')"
            @update:model-value="localRule.preferred_group = String($event)"
          />
        </div>

        <div class="weekday-row">
          <label class="weekday-label">{{
            $t('homepage.rule.preferred_resolution')
          }}</label>
          <NSelect
            v-model:value="localRule.preferred_resolution"
            :options="resolutionOptions"
            role="combobox"
            aria-haspopup="listbox"
            :menu-props="selectMenuProps"
            :node-props="selectOptionNodeProps"
            clearable
            filterable
            tag
            size="small"
            :placeholder="$t('homepage.rule.auto_detect')"
            :aria-label="$t('homepage.rule.preferred_resolution')"
            class="weekday-select"
          />
        </div>

        <p class="preferred-hint">
          {{ $t('homepage.rule.preferred_hint') }}
        </p>
      </advanced-section>
    </div>

    <!-- 删除确认：嵌套在主弹窗组件树内，headlessui 才会把外层的
         Escape/遮罩点击挂起，只关闭内层 -->
    <!-- Delete confirmation dialog -->
    <ab-modal
      v-if="!isMobile"
      v-model:show="deleteFileDialog.show"
      size="sm"
      :title="$t('homepage.rule.delete')"
    >
      <p class="delete-message">
        {{ $t('homepage.rule.delete_confirm') }}
      </p>
      <NCheckbox v-model:checked="deleteLocalFiles" class="delete-files-option">
        {{ $t('homepage.rule.delete_files_label') }}
      </NCheckbox>

      <template #footer>
        <ab-button size="sm" @click="deleteFileDialog.show = false">
          {{ $t('homepage.rule.cancel_btn') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="danger"
          @click="emitDeleteFile(deleteLocalFiles)"
        >
          {{ $t('homepage.rule.delete') }}
        </ab-button>
      </template>
    </ab-modal>

    <template #footer>
      <template v-if="mobileDeleteActive">
        <ab-button size="sm" @click="returnToEditor">
          {{ $t('homepage.rule.cancel_btn') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="danger"
          @click="emitDeleteFile(deleteLocalFiles)"
        >
          {{ $t('homepage.rule.delete') }}
        </ab-button>
      </template>
      <template v-else-if="isMobile">
        <div ref="mobileActionsRef" class="rule-mobile-actions">
          <ab-menu :items="mobileRuleActions" align="left" placement="top">
            <template #trigger>
              <ab-icon-button :label="$t('common.moreActions')">
                <More :size="20" />
              </ab-icon-button>
            </template>
          </ab-menu>
        </div>
        <ab-button
          variant="primary"
          size="sm"
          class="rule-mobile-apply"
          @click="emitApply"
        >
          {{ $t('homepage.rule.apply') }}
        </ab-button>
      </template>
      <template v-else>
        <ab-button size="sm" variant="ghost" @click="goToTorrents">
          {{ $t('homepage.rule.view_torrents') }}
        </ab-button>
        <ab-button v-if="localRule.archived" size="sm" @click="emitUnarchive">
          {{ $t('homepage.rule.unarchive') }}
        </ab-button>
        <ab-button v-else size="sm" @click="emitArchive">
          {{ $t('homepage.rule.archive') }}
        </ab-button>
        <ab-button
          size="sm"
          variant="danger"
          class="footer-delete"
          @click="showDeleteFileDialog"
        >
          {{ $t('homepage.rule.delete') }}
        </ab-button>
        <ab-button variant="primary" size="sm" @click="emitApply">
          {{ $t('homepage.rule.apply') }}
        </ab-button>
      </template>
    </template>
  </ab-modal>
</template>

<style lang="scss" scoped>
// Review warning banner
.review-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  margin: 12px 20px;
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
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
  color: var(--color-warning-text);
}

.review-warning-reason {
  font-size: 12px;
  color: var(--color-warning-text-secondary);
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
  display: flex;
  flex-direction: column;
  gap: 14px;
}

// 归档/删除靠左，应用靠右
.footer-delete {
  margin-right: auto;
}

// Footer
// Delete confirmation dialog
.delete-message {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
}

.delete-files-option {
  margin-bottom: 20px;
}

.weekday-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 32px;
}

.weekday-label {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.weekday-select {
  max-width: 160px;
}

.preferred-input {
  width: 160px;
  max-width: 160px;
}

.preferred-hint {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-secondary);
}

@media screen and (max-width: 639px) {
  .weekday-row {
    align-items: stretch;
    flex-direction: column;
    gap: 6px;
  }

  .weekday-select,
  .preferred-input {
    width: 100%;
    max-width: none;
  }

  .review-warning {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
    margin: 8px 0;
    padding: 10px 12px;
  }

  .review-warning-actions {
    width: 100%;
    flex-shrink: 1;
  }

  .review-warning-actions .detect-btn,
  .review-warning-actions .dismiss-btn {
    height: var(--touch-target);
    min-width: 0;
    flex: 1;
  }

  .rule-mobile-actions {
    margin-right: auto;
  }

  .rule-mobile-actions :deep(.ab-icon-btn),
  .rule-mobile-apply {
    min-width: var(--touch-target);
    min-height: var(--touch-target);
  }
}
</style>
