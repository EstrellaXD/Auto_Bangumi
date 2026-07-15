<script lang="ts" setup>
import { More, Refresh } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';
import type { AbMenuItem } from '@/components/basic/ab-menu.vue';
import { useFocusHandoff } from '@/hooks/useFocusHandoff';

definePage({
  name: 'Bangumi List',
});

const {
  bangumi,
  showArchived,
  isLoading,
  hasLoaded,
  loadFailed,
  activeBangumi,
  archivedBangumi,
} = storeToRefs(useBangumiStore());
const { getAll, openEditPopup, refreshPoster } = useBangumiStore();
const { openAddRss } = useAddRss();
const { isMobile } = useBreakpointQuery();
const { t } = useMyI18n();

const mobileActions: AbMenuItem[] = [
  {
    key: 'refresh-posters',
    label: () => t('topbar.refresh_poster'),
    icon: Refresh,
    handler: async () => {
      await refreshPoster();
    },
  },
];

// Show skeleton when initially loading (not yet loaded and loading)
const showSkeleton = computed(() => !hasLoaded.value && isLoading.value);
const skeletonCount = 8; // Number of skeleton cards to show

const refreshing = ref(false);

// Orphan torrents count for the Others card
const orphanCount = ref(0);

async function loadOrphanCount() {
  try {
    orphanCount.value = await apiBangumi.getOrphanTorrentCount();
  } catch {
    orphanCount.value = 0;
  }
}

const router = useRouter();

function goToOrphans() {
  router.push('/bangumi-torrents/orphans');
}

async function onRefresh() {
  refreshing.value = true;
  try {
    await Promise.all([getAll(), loadOrphanCount()]);
  } finally {
    refreshing.value = false;
  }
}

onActivated(() => {
  getAll();
  loadOrphanCount();
});

// Group bangumi by official_title + season
interface BangumiGroup {
  key: string;
  primary: BangumiRule;
  rules: BangumiRule[];
}

function groupBangumi(items: BangumiRule[]): BangumiGroup[] {
  if (!items) return [];
  const map = new Map<string, BangumiRule[]>();
  for (const item of items) {
    const key = `${item.official_title}::${item.season}`;
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key)!.push(item);
  }
  const groups: BangumiGroup[] = [];
  for (const [key, rules] of map) {
    groups.push({ key, primary: rules[0], rules });
  }
  return groups;
}

const groupedBangumi = computed<BangumiGroup[]>(() =>
  groupBangumi(activeBangumi.value)
);
const groupedArchivedBangumi = computed<BangumiGroup[]>(() =>
  groupBangumi(archivedBangumi.value)
);

// Rule list popup state
const ruleListPopup = reactive<{
  show: boolean;
  group: BangumiGroup | null;
}>({
  show: false,
  group: null,
});
const pendingEditRule = ref<BangumiRule | null>(null);
const { captureFocusTarget, restoreFocusTarget } = useFocusHandoff();

function onCardClick(group: BangumiGroup) {
  if (group.rules.length === 1) {
    openEditPopup(group.primary);
  } else {
    captureFocusTarget();
    ruleListPopup.group = group;
    ruleListPopup.show = true;
  }
}

function onRuleSelect(rule: BangumiRule) {
  pendingEditRule.value = rule;
  ruleListPopup.show = false;
}

function onRuleListAfterLeave() {
  const rule = pendingEditRule.value;
  if (!rule) return;
  pendingEditRule.value = null;
  restoreFocusTarget();
  openEditPopup(rule);
}

// Check if any rule in group needs review
function groupNeedsReview(group: BangumiGroup): boolean {
  return group.rules.some((r) => r.needs_review);
}
</script>

<template>
  <ab-pull-refresh :loading="refreshing" @refresh="onRefresh">
    <div class="page-bangumi">
      <div v-if="isMobile" class="bangumi-mobile-toolbar">
        <ab-menu :items="mobileActions" align="right">
          <template #trigger>
            <ab-icon-button :label="t('common.moreActions')">
              <More :size="20" />
            </ab-icon-button>
          </template>
        </ab-menu>
      </div>

      <!-- Skeleton loading state -->
      <div v-if="showSkeleton" class="bangumi-grid">
        <div
          v-for="i in skeletonCount"
          :key="`skeleton-${i}`"
          class="skeleton-card"
        >
          <div class="skeleton-poster"></div>
          <div class="skeleton-title"></div>
        </div>
      </div>

      <!-- Failed first load — distinct from an empty library -->
      <div v-else-if="loadFailed && !hasLoaded" class="empty-guide load-failed">
        <div class="empty-guide-header">
          <div class="empty-guide-title">
            {{ $t('homepage.load_failed.title') }}
          </div>
          <div class="empty-guide-subtitle">
            {{ $t('homepage.load_failed.subtitle') }}
          </div>
        </div>
        <ab-button variant="primary" :loading="isLoading" @click="getAll">
          {{ $t('homepage.load_failed.retry') }}
        </ab-button>
      </div>

      <!-- Empty state guide -->
      <div v-else-if="!bangumi || bangumi.length === 0" class="empty-guide">
        <div class="empty-guide-header anim-fade-in">
          <div class="empty-guide-title">{{ $t('homepage.empty.title') }}</div>
          <div class="empty-guide-subtitle">
            {{ $t('homepage.empty.subtitle') }}
          </div>
        </div>

        <div class="empty-guide-steps">
          <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
            <div class="empty-guide-step-number">1</div>
            <div class="empty-guide-step-content">
              <div class="empty-guide-step-title">
                {{ $t('homepage.empty.step1_title') }}
              </div>
              <div class="empty-guide-step-desc">
                {{ $t('homepage.empty.step1_desc') }}
              </div>
            </div>
          </div>

          <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
            <div class="empty-guide-step-number">2</div>
            <div class="empty-guide-step-content">
              <div class="empty-guide-step-title">
                {{ $t('homepage.empty.step2_title') }}
              </div>
              <div class="empty-guide-step-desc">
                {{ $t('homepage.empty.step2_desc') }}
              </div>
            </div>
          </div>

          <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
            <div class="empty-guide-step-number">3</div>
            <div class="empty-guide-step-content">
              <div class="empty-guide-step-title">
                {{ $t('homepage.empty.step3_title') }}
              </div>
              <div class="empty-guide-step-desc">
                {{ $t('homepage.empty.step3_desc') }}
              </div>
            </div>
          </div>
        </div>

        <div class="empty-guide-action anim-slide-up" style="--delay: 0.6s">
          <ab-button variant="primary" @click="openAddRss">
            {{ $t('homepage.empty.add_rss_btn') }}
          </ab-button>
        </div>
      </div>

      <!-- Bangumi grid -->
      <template v-else>
        <transition-group name="bangumi" tag="div" class="bangumi-grid">
          <div
            v-for="group in groupedBangumi"
            :key="group.key"
            class="bangumi-group-wrapper"
            :class="[group.rules.every((r) => r.deleted) && 'grayscale']"
          >
            <ab-bangumi-card
              :bangumi="group.primary"
              type="primary"
              @click="() => onCardClick(group)"
            />
            <!-- Combined notification badge -->
            <div
              v-if="groupNeedsReview(group) || group.rules.length > 1"
              class="group-badge"
              :class="{ 'group-badge--warning': groupNeedsReview(group) }"
            >
              <template v-if="groupNeedsReview(group)">
                <span class="badge-icon">!</span>
                <template v-if="group.rules.length > 1">
                  <span class="badge-divider"></span>
                  <span class="badge-count">{{ group.rules.length }}</span>
                </template>
              </template>
              <template v-else>
                {{ group.rules.length }}
              </template>
            </div>
          </div>

          <!-- Others card for orphan torrents -->
          <div
            v-if="orphanCount > 0"
            key="__others__"
            class="others-card"
            role="button"
            tabindex="0"
            @click="goToOrphans"
            @keydown.enter="goToOrphans"
          >
            <div class="others-poster">
              <span class="others-icon">?</span>
              <ab-badge :count="orphanCount" class="others-count" />
            </div>
            <div class="others-info">
              <div class="others-title">{{ $t('homepage.others.title') }}</div>
            </div>
          </div>
        </transition-group>

        <!-- Archived section -->
        <div v-if="groupedArchivedBangumi.length > 0" class="archived-section">
          <button
            type="button"
            class="archived-header"
            :aria-expanded="showArchived"
            @click="showArchived = !showArchived"
          >
            <span class="archived-title">
              {{
                $t('homepage.rule.archived_section', {
                  count: archivedBangumi.length,
                })
              }}
            </span>
            <span class="archived-toggle" aria-hidden="true">{{
              showArchived ? '−' : '+'
            }}</span>
          </button>

          <transition-group
            v-show="showArchived"
            name="bangumi"
            tag="div"
            class="bangumi-grid archived-grid"
          >
            <div
              v-for="group in groupedArchivedBangumi"
              :key="group.key"
              class="bangumi-group-wrapper archived-item"
            >
              <ab-bangumi-card
                :bangumi="group.primary"
                type="primary"
                @click="() => onCardClick(group)"
              />
              <!-- Combined notification badge -->
              <div
                v-if="groupNeedsReview(group) || group.rules.length > 1"
                class="group-badge"
                :class="{ 'group-badge--warning': groupNeedsReview(group) }"
              >
                <template v-if="groupNeedsReview(group)">
                  <span class="badge-icon">!</span>
                  <template v-if="group.rules.length > 1">
                    <span class="badge-divider"></span>
                    <span class="badge-count">{{ group.rules.length }}</span>
                  </template>
                </template>
                <template v-else>
                  {{ group.rules.length }}
                </template>
              </div>
              <div class="archived-badge">
                {{ $t('homepage.rule.archived') }}
              </div>
            </div>
          </transition-group>
        </div>
      </template>

      <!-- Rule list popup for grouped items -->
      <ab-modal
        v-model:show="ruleListPopup.show"
        :title="ruleListPopup.group?.primary.official_title || ''"
        @after-leave="onRuleListAfterLeave"
      >
        <div v-if="ruleListPopup.group" class="rule-list">
          <div class="rule-list-hint">
            {{ $t('homepage.rule.select_hint') }}
          </div>
          <div
            v-for="rule in ruleListPopup.group.rules"
            :key="rule.id"
            class="rule-list-item"
            :class="[
              rule.deleted && 'rule-list-item--disabled',
              rule.needs_review && 'rule-list-item--warning',
            ]"
            @click="onRuleSelect(rule)"
          >
            <div class="rule-list-item-info">
              <div class="rule-list-item-title">
                <span v-if="rule.needs_review" class="warning-text">! </span
                >{{
                  rule.group_name ||
                  rule.rule_name ||
                  $t('homepage.rule.unnamed')
                }}
              </div>
              <div class="rule-list-item-tags">
                <ab-tag v-if="rule.dpi" :title="rule.dpi" type="info" />
                <ab-tag
                  v-if="rule.subtitle"
                  :title="rule.subtitle"
                  type="info"
                />
                <ab-tag v-if="rule.source" :title="rule.source" type="info" />
              </div>
              <div
                v-if="rule.filter && rule.filter.length > 0"
                class="rule-list-item-filter"
              >
                <span class="rule-list-item-filter-label"
                  >{{ $t('homepage.rule.filter') }}:</span
                >
                <span class="rule-list-item-filter-value">{{
                  rule.filter.join(', ')
                }}</span>
              </div>
              <div v-if="rule.title_raw" class="rule-list-item-raw">
                {{ rule.title_raw }}
              </div>
            </div>
            <div class="rule-list-item-arrow">›</div>
          </div>
        </div>
      </ab-modal>
    </div>
  </ab-pull-refresh>
</template>

<style lang="scss" scoped>
.page-bangumi {
  overflow: auto;
  flex-grow: 1;
}

.bangumi-mobile-toolbar {
  display: flex;
  justify-content: flex-end;
  min-height: var(--touch-target);
  padding: 0 2px;
}

.bangumi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  padding: 12px;
  justify-items: center;

  @include forTablet {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 16px;
  }

  @include forDesktop {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 20px;
  }
}

// Skeleton loading cards
.skeleton-card {
  width: 150px;
}

.skeleton-poster {
  width: 100%;
  aspect-ratio: 5 / 7;
  border-radius: var(--radius-md);
  background: linear-gradient(
    90deg,
    var(--color-surface-hover) 25%,
    var(--color-border) 50%,
    var(--color-surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
}

.skeleton-title {
  height: 16px;
  margin-top: 8px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--color-surface-hover) 25%,
    var(--color-border) 50%,
    var(--color-surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  animation-delay: 0.1s;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

// Others card for orphan torrents
.others-card {
  width: 150px;
  cursor: pointer;
  user-select: none;

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 4px;
    border-radius: var(--radius-md);
  }
}

.others-poster {
  position: relative;
  aspect-ratio: 5 / 7;
  border-radius: var(--radius-md);
  overflow: visible;
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  border: 2px dashed var(--color-border);
  transition: box-shadow var(--transition-fast),
    transform var(--transition-fast);

  .others-card:hover &,
  .others-card:focus-visible & {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
  }

  @include forTouch {
    .others-card:hover & {
      transform: none;
    }
  }
}

.others-icon {
  font-size: 48px;
  font-weight: 700;
  color: var(--color-text-muted);
}

.others-count {
  position: absolute;
  top: -8px;
  right: -8px;
  z-index: 10;
}

.others-info {
  padding: 8px 2px 4px;
}

.others-title {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bangumi-group-wrapper {
  position: relative;
  overflow: visible;
  width: fit-content;
}

.group-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(124, 77, 255, 0.4);

  // Warning variant - yellow with purple border
  &--warning {
    background: var(--color-warning);
    border: 2px solid var(--color-primary);
    color: var(--color-primary);
    box-shadow: 0 2px 8px rgba(251, 191, 36, 0.5);
  }

  .badge-icon {
    font-weight: 800;
  }

  .badge-divider {
    width: 1px;
    height: 10px;
    background: currentColor;
    opacity: 0.5;
  }

  .badge-count {
    font-weight: 700;
  }
}

.archived-section {
  margin-top: 24px;
  padding: 0 8px;
}

.archived-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px 8px;
  margin-bottom: 12px;
  cursor: pointer;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  font: inherit;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.archived-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.archived-toggle {
  font-size: 18px;
  font-weight: 500;
  color: var(--color-text-muted);
}

.archived-grid {
  opacity: 0.7;
}

.archived-item {
  filter: grayscale(30%);
}

.archived-badge {
  position: absolute;
  bottom: 36px; // Above the card title area
  left: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-overlay);
  backdrop-filter: blur(4px);
  color: var(--color-white);
  font-size: 10px;
  font-weight: 500;
  pointer-events: none;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  min-width: min(300px, 100%);
}

.rule-list-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 4px 12px 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

.rule-list-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-height: var(--touch-target);
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  &--disabled {
    opacity: 0.5;
  }

  // Warning variant - needs review
  &--warning {
    background: linear-gradient(
      135deg,
      rgba(251, 191, 36, 0.15) 0%,
      rgba(251, 191, 36, 0.08) 100%
    );
    border-left: 3px solid var(--color-warning);

    &:hover {
      background: linear-gradient(
        135deg,
        rgba(251, 191, 36, 0.22) 0%,
        rgba(251, 191, 36, 0.12) 100%
      );
    }
  }

  // Add spacing between items
  & + & {
    margin-top: 8px;
  }
}

.warning-text {
  color: #d97706;
  font-weight: 700;
}

.rule-list-item-info {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.rule-list-item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-list-item-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.rule-list-item-filter {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-list-item-filter-label {
  color: var(--color-text-secondary);
}

.rule-list-item-filter-value {
  font-family: var(--font-mono, monospace);
}

.rule-list-item-raw {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-style: italic;
}

.rule-list-item-arrow {
  font-size: 18px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  margin-top: 2px;
}

.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 24px;
}

.empty-guide-header {
  text-align: center;
  margin-bottom: 32px;
}

.empty-guide-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.empty-guide-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.empty-guide-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 400px;
  width: 100%;
}

.empty-guide-action {
  margin-top: 24px;
}

.empty-guide-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  transition: background-color var(--transition-normal),
    border-color var(--transition-normal);
}

.empty-guide-step-number {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-white);
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-guide-step-content {
  flex: 1;
  min-width: 0;
}

.empty-guide-step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.empty-guide-step-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.anim-fade-in {
  animation: fadeIn 0.5s ease both;
}

.anim-slide-up {
  animation: slideUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay, 0s);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media screen and (max-width: 639px) {
  .page-bangumi {
    min-width: 0;
    overflow-x: hidden;
  }

  .bangumi-mobile-toolbar :deep(.ab-icon-btn) {
    width: var(--touch-target);
    height: var(--touch-target);
  }

  .bangumi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    padding: 8px 2px 12px;
    justify-items: stretch;
  }

  .bangumi-group-wrapper,
  .skeleton-card,
  .others-card,
  :deep(.card) {
    width: 100%;
    min-width: 0;
  }

  .group-badge,
  .others-count {
    top: -6px;
    right: 2px;
  }

  .archived-section {
    margin-top: 16px;
    padding: 0;
  }

  .archived-header {
    min-height: var(--touch-target);
    margin-bottom: 4px;
  }
}
</style>

<style>
.bangumi-enter-active,
.bangumi-leave-active {
  transition: opacity var(--transition-normal),
    transform var(--transition-normal);
}
.bangumi-enter-from,
.bangumi-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
