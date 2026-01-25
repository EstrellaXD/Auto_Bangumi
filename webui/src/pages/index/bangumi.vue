<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

definePage({
  name: 'Bangumi List',
});

const { bangumi, showArchived, isLoading, hasLoaded, activeBangumi, archivedBangumi } = storeToRefs(useBangumiStore());
const { getAll, openEditPopup } = useBangumiStore();

// Show skeleton when initially loading (not yet loaded and loading)
const showSkeleton = computed(() => !hasLoaded.value && isLoading.value);
const skeletonCount = 8; // Number of skeleton cards to show

const refreshing = ref(false);

async function onRefresh() {
  refreshing.value = true;
  try {
    await getAll();
  } finally {
    refreshing.value = false;
  }
}

onActivated(() => {
  getAll();
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

const groupedBangumi = computed<BangumiGroup[]>(() => groupBangumi(activeBangumi.value));
const groupedArchivedBangumi = computed<BangumiGroup[]>(() => groupBangumi(archivedBangumi.value));

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
</script>

<template>
  <ab-pull-refresh :loading="refreshing" @refresh="onRefresh">
  <div class="page-bangumi">
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

    <!-- Empty state guide -->
    <div v-else-if="!bangumi || bangumi.length === 0" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">{{ $t('homepage.empty.title') }}</div>
        <div class="empty-guide-subtitle">{{ $t('homepage.empty.subtitle') }}</div>
      </div>

      <div class="empty-guide-steps">
        <div class="empty-guide-step anim-slide-up" style="--delay: 0.15s">
          <div class="empty-guide-step-number">1</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step1_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step1_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.3s">
          <div class="empty-guide-step-number">2</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step2_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step2_desc') }}</div>
          </div>
        </div>

        <div class="empty-guide-step anim-slide-up" style="--delay: 0.45s">
          <div class="empty-guide-step-number">3</div>
          <div class="empty-guide-step-content">
            <div class="empty-guide-step-title">{{ $t('homepage.empty.step3_title') }}</div>
            <div class="empty-guide-step-desc">{{ $t('homepage.empty.step3_desc') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bangumi grid -->
    <template v-else>
      <transition-group
        name="bangumi"
        tag="div"
        class="bangumi-grid"
      >
        <div
          v-for="group in groupedBangumi"
          :key="group.key"
          class="bangumi-group-wrapper"
          :class="[group.rules.every(r => r.deleted) && 'grayscale']"
        >
          <ab-bangumi-card
            :bangumi="group.primary"
            type="primary"
            @click="() => onCardClick(group)"
          />
          <div v-if="group.rules.length > 1" class="group-badge">
            {{ group.rules.length }}
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
            {{ $t('homepage.rule.archived_section', { count: archivedBangumi.length }) }}
          </span>
          <span class="archived-toggle" aria-hidden="true">{{ showArchived ? '−' : '+' }}</span>
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
            <div v-if="group.rules.length > 1" class="group-badge">
              {{ group.rules.length }}
            </div>
            <div class="archived-badge">{{ $t('homepage.rule.archived') }}</div>
          </div>
        </transition-group>
      </div>
    </template>

    <!-- Rule list popup for grouped items -->
    <ab-popup
      v-model:show="ruleListPopup.show"
      :title="ruleListPopup.group?.primary.official_title || ''"
    >
      <div v-if="ruleListPopup.group" class="rule-list">
        <div
          v-for="rule in ruleListPopup.group.rules"
          :key="rule.id"
          class="rule-list-item"
          :class="[rule.deleted && 'rule-list-item--disabled']"
          @click="onRuleSelect(rule)"
        >
          <div class="rule-list-item-info">
            <div class="rule-list-item-title">
              {{ rule.group_name || rule.rule_name || `Rule #${rule.id}` }}
            </div>
            <div class="rule-list-item-meta">
              <span v-if="rule.dpi">{{ rule.dpi }}</span>
              <span v-if="rule.subtitle">{{ rule.subtitle }}</span>
              <span v-if="rule.source">{{ rule.source }}</span>
            </div>
          </div>
          <div class="rule-list-item-arrow">›</div>
        </div>
      </div>
    </ab-popup>

  </div>
  </ab-pull-refresh>
</template>

<style lang="scss" scoped>
.page-bangumi {
  overflow: auto;
  flex-grow: 1;
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

.bangumi-group-wrapper {
  position: relative;
  overflow: visible;
  width: fit-content;
}

.group-badge {
  position: absolute;
  top: -10px;
  right: -10px;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 11px;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  pointer-events: none;
  box-shadow: 0 2px 6px rgba(124, 77, 255, 0.4);
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
  bottom: 4px;
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
  gap: 2px;
  padding: 8px;
  min-width: 280px;
}

.rule-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: var(--touch-target);
  padding: 10px 12px;
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
}

.rule-list-item-info {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.rule-list-item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-list-item-meta {
  display: flex;
  gap: 8px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-secondary);

  span + span::before {
    content: '·';
    margin-right: 8px;
    color: var(--color-text-muted);
  }
}

.rule-list-item-arrow {
  font-size: 18px;
  color: var(--color-text-muted);
  flex-shrink: 0;
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
</style>

<style>
.bangumi-enter-active,
.bangumi-leave-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}
.bangumi-enter-from,
.bangumi-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
