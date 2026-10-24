<script lang="ts" setup>
import { ChevronDown } from '@lucide/vue';
import type { BangumiRule } from '#/bangumi';
import PluginSlot from '@/components/plugin-slot.vue';
import { useUiSlots } from '@/hooks/usePluginUi';

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
const { getAll, openEditPopup } = useBangumiStore();
const { openAddRss } = useAddRss();

// 插件经 dashboard.widget 挂载点追加的小组件
const widgets = useUiSlots('dashboard.widget');

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

function onCardClick(group: BangumiGroup) {
  if (group.rules.length === 1) {
    openEditPopup(group.primary);
  } else {
    ruleListPopup.group = group;
    ruleListPopup.show = true;
  }
}

function onRuleSelect(rule: BangumiRule) {
  ruleListPopup.show = false;
  openEditPopup(rule);
}

// Check if any rule in group needs review
function groupNeedsReview(group: BangumiGroup): boolean {
  return group.rules.some((r) => r.needs_review);
}

// 展开后归档内容在视口外：高度过渡结束（可滚动范围已够）后把折叠栏滚到顶部
const archivedHeader = useTemplateRef<HTMLButtonElement>('archivedHeader');
function onArchivedExpanded(e: TransitionEvent) {
  if (e.target !== e.currentTarget || !showArchived.value) return;
  archivedHeader.value?.scrollIntoView({ block: 'start', behavior: 'smooth' });
}

// 离场卡片绝对定位脱离文档流（其余卡片才能 FLIP 移位），先钉住原来的盒子
function pinLeaving(el: Element) {
  const node = el as HTMLElement;
  node.style.width = `${node.offsetWidth}px`;
  node.style.left = `${node.offsetLeft}px`;
  node.style.top = `${node.offsetTop}px`;
}
</script>

<template>
  <ab-pull-refresh :loading="refreshing" @refresh="onRefresh">
    <div class="page-bangumi">
      <div v-if="widgets.length" class="plugin-widgets">
        <PluginSlot
          v-for="ui in widgets"
          :key="`${ui.plugin_id}:${ui.element}`"
          :ui="ui"
        />
      </div>

      <!-- Skeleton loading state -->
      <div v-if="showSkeleton" class="bangumi-grid">
        <div
          v-for="i in skeletonCount"
          :key="`skeleton-${i}`"
          class="skeleton-card"
        >
          <div class="skeleton-poster" />
          <div class="skeleton-title" />
        </div>
      </div>

      <!-- Failed first load — distinct from an empty library -->
      <div v-else-if="loadFailed && !hasLoaded" class="page-empty">
        <ab-empty
          :title="$t('homepage.load_failed.title')"
          :description="$t('homepage.load_failed.subtitle')"
        >
          <template #action>
            <ab-button variant="primary" :loading="isLoading" @click="getAll">
              {{ $t('homepage.load_failed.retry') }}
            </ab-button>
          </template>
        </ab-empty>
      </div>

      <!-- Empty state guide -->
      <div v-else-if="!bangumi || bangumi.length === 0" class="page-empty">
        <ab-empty
          :title="$t('homepage.empty.title')"
          :description="$t('homepage.empty.subtitle')"
        >
          <template #action>
            <ol class="empty-steps" role="list">
              <li v-for="n in 3" :key="n">
                <span class="empty-steps-title">{{
                  $t(`homepage.empty.step${n}_title`)
                }}</span>
                {{ $t(`homepage.empty.step${n}_desc`) }}
              </li>
            </ol>
            <ab-button variant="primary" @click="openAddRss">
              {{ $t('homepage.empty.add_rss_btn') }}
            </ab-button>
          </template>
        </ab-empty>
      </div>

      <!-- Bangumi grid -->
      <template v-else>
        <transition-group
          name="bangumi"
          tag="div"
          class="bangumi-grid"
          @before-leave="pinLeaving"
        >
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
            <!-- Combined notification badge：待审核 = 方块标记，多规则 = 墨色计数 -->
            <div
              v-if="groupNeedsReview(group) || group.rules.length > 1"
              class="group-badge"
            >
              <span v-if="groupNeedsReview(group)" class="badge-mark" />
              <template v-if="group.rules.length > 1">
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
              <div class="others-title">
                {{ $t('homepage.others.title') }}
              </div>
            </div>
          </div>
        </transition-group>

        <!-- Archived section -->
        <div v-if="groupedArchivedBangumi.length > 0" class="archived-section">
          <button
            ref="archivedHeader"
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
            <ChevronDown
              class="archived-toggle"
              :class="{ 'archived-toggle--open': showArchived }"
              :size="16"
              aria-hidden="true"
            />
          </button>

          <!-- grid-template-rows 0fr↔1fr 做高度过渡；收起时 inert，卡片不可聚焦 -->
          <div
            class="archived-body"
            :class="{ 'archived-body--open': showArchived }"
            :inert="!showArchived"
            @transitionend="onArchivedExpanded"
          >
            <!-- 裁剪层不带 padding：网格的 12px padding 不会在收起时撑出 24px 高度 -->
            <div class="archived-clip">
              <transition-group
                name="bangumi"
                tag="div"
                class="bangumi-grid archived-grid"
                @before-leave="pinLeaving"
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
                  <div
                    v-if="groupNeedsReview(group) || group.rules.length > 1"
                    class="group-badge"
                  >
                    <span v-if="groupNeedsReview(group)" class="badge-mark" />
                    <template v-if="group.rules.length > 1">
                      {{ group.rules.length }}
                    </template>
                  </div>
                  <div class="archived-badge">
                    {{ $t('homepage.rule.archived') }}
                  </div>
                </div>
              </transition-group>
            </div>
          </div>
        </div>
      </template>

      <!-- Rule list popup for grouped items -->
      <ab-modal
        v-model:show="ruleListPopup.show"
        :title="ruleListPopup.group?.primary.official_title || ''"
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
              <div
                class="rule-list-item-title"
                :title="rule.needs_review ? $t('homepage.rule.needs_review') : undefined"
              >
                {{
                  rule.group_name
                    || rule.rule_name
                    || $t('homepage.rule.unnamed')
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
                <span class="rule-list-item-filter-label">{{ $t('homepage.rule.filter') }}:</span>
                <span class="rule-list-item-filter-value">{{
                  rule.filter.join(', ')
                }}</span>
              </div>
              <div v-if="rule.title_raw" class="rule-list-item-raw">
                {{ rule.title_raw }}
              </div>
            </div>
            <div class="rule-list-item-arrow">
              ›
            </div>
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

.plugin-widgets {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--layout-gap);
  padding: 12px 12px 0;
}

.bangumi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  padding: 12px;
  // 离场卡片绝对定位时以网格为参照（见 pinLeaving）
  position: relative;

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
  width: 100%;
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
  width: 100%;
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
  width: 100%;
}

// 离场卡片脱离文档流，其余卡片才会触发 .bangumi-move 位移（盒子由 pinLeaving 钉住）
.bangumi-grid > .bangumi-leave-active {
  position: absolute;
}

// Soft Ink：surface 底 + 墨色计数，待审核用语义色方块标记，不用彩色填充/光晕
.group-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  z-index: 10;
  pointer-events: none;
  box-shadow: var(--shadow-sm);

  .badge-mark {
    width: 7px;
    height: 7px;
    border-radius: 2px;
    background: var(--color-warning);
  }
}

.archived-section {
  margin-top: 24px;
}

// 左右 padding 与 .bangumi-grid 的 12px 一致，标题文字与海报共用左边线
.archived-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 12px;
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
  flex-shrink: 0;
  color: var(--color-text-secondary);
  transition: transform var(--transition-normal);

  &--open {
    transform: rotate(180deg);
  }
}

.archived-body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows var(--transition-normal);

  > .archived-clip {
    min-height: 0;
    overflow: hidden;
  }

  &--open {
    grid-template-rows: 1fr;
  }
}

.archived-grid {
  opacity: 0.7;
}

.archived-item {
  filter: grayscale(30%);
}

.archived-badge {
  position: absolute;
  top: 6px; // 海报左上角，不随标题高度移动
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

  // 待审核：内阴影画左侧标记，不改变盒宽（与通知中心未读项同一写法）
  &--warning {
    box-shadow: inset 3px 0 0 var(--color-warning);
  }

  // Add spacing between items
  & + & {
    margin-top: 8px;
  }
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

.page-empty {
  padding: 12px;
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
.bangumi-move {
  transition: transform var(--transition-normal);
}
</style>
