<script lang="ts" setup>
import { Refresh } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';
import type { BangumiGroup } from '@/components/calendar/types';

definePage({
  name: 'Calendar',
});

const { bangumi } = storeToRefs(useBangumiStore());
const { getAll, openEditPopup } = useBangumiStore();
const { isMobile } = useBreakpointQuery();
const { t } = useMyI18n();

const refreshing = ref(false);
const message = useMessage();

async function refreshCalendar() {
  refreshing.value = true;
  try {
    await apiBangumi.refreshCalendar();
    await getAll();
    message.success(t('calendar.refresh_success'));
  } catch {
    // Failure toast already shown by the axios interceptor.
  } finally {
    refreshing.value = false;
  }
}

onActivated(() => {
  // Re-read local state on tab activation; the bangumi.tv scrape + DB write
  // in refreshCalendar() is reserved for the explicit refresh button.
  getAll();
});

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

const todayIndex = computed(() => {
  // JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat
  // We want: 0=Mon, 1=Tue, ..., 6=Sun
  const jsDay = new Date().getDay();
  return jsDay === 0 ? 6 : jsDay - 1;
});

// Group bangumi by official_title + season (same logic as main page)
function groupBangumiList(items: BangumiRule[]): BangumiGroup[] {
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

const groupedBangumiByDay = computed(() => {
  const result: Record<string, BangumiGroup[]> = {};
  DAY_KEYS.forEach((key) => (result[key] = []));
  result.unknown = [];

  // First, collect items by day
  const itemsByDay: Record<string, BangumiRule[]> = {};
  DAY_KEYS.forEach((key) => (itemsByDay[key] = []));
  itemsByDay.unknown = [];

  bangumi.value?.forEach((item) => {
    if (item.deleted) return;
    const weekday = item.air_weekday;
    if (weekday != null && weekday >= 0 && weekday <= 6) {
      itemsByDay[DAY_KEYS[weekday]].push(item);
    } else {
      itemsByDay.unknown.push(item);
    }
  });

  // Then group each day's items
  for (const key of [...DAY_KEYS, 'unknown']) {
    result[key] = groupBangumiList(itemsByDay[key]);
  }

  return result;
});

const hasBangumi = computed(() => {
  return bangumi.value && bangumi.value.some((b) => !b.deleted);
});

function getDayLabel(key: string): string {
  if (key === 'unknown') return t('calendar.unknown');
  return isMobile.value
    ? t(`calendar.days.${key}`)
    : t(`calendar.days_short.${key}`);
}

// Rule list popup state (same as main page)
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
  <div class="page-calendar">
    <!-- Header -->
    <div class="calendar-header anim-fade-in">
      <!-- 页面本身已有 h1 “Calendar”，这里不再重复标题，只留说明文字 -->
      <div class="calendar-header-text">
        <p class="calendar-subtitle">{{ $t('calendar.subtitle') }}</p>
      </div>
      <ab-icon-button
        class="calendar-refresh-btn"
        :class="{ 'calendar-refresh-btn--spinning': refreshing }"
        :disabled="refreshing"
        :label="$t('calendar.refresh')"
        @click="refreshCalendar"
      >
        <Refresh :size="18" />
      </ab-icon-button>
    </div>

    <!-- Empty state -->
    <div v-if="!hasBangumi" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">
          {{ $t('calendar.empty_state.title') }}
        </div>
        <div class="empty-guide-subtitle">
          {{ $t('calendar.empty_state.subtitle') }}
        </div>
      </div>
    </div>

    <!-- Desktop: board of day columns -->
    <calendar-board
      v-else-if="!isMobile"
      :day-keys="DAY_KEYS"
      :grouped-by-day="groupedBangumiByDay"
      :today-index="todayIndex"
      :get-day-label="getDayLabel"
      @card-click="onCardClick"
    />

    <!-- Mobile: vertical list -->
    <calendar-mobile-list
      v-else
      :day-keys="[...DAY_KEYS, 'unknown']"
      :grouped-by-day="groupedBangumiByDay"
      :today-index="todayIndex"
      :get-day-label="getDayLabel"
      :has-bangumi="hasBangumi"
      @card-click="onCardClick"
    />

    <!-- Rule list popup for grouped items -->
    <calendar-rule-list-popup
      v-model:show="ruleListPopup.show"
      :group="ruleListPopup.group"
      @select="onRuleSelect"
    />
  </div>
</template>

<style lang="scss" scoped>
.page-calendar {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// Header
.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.calendar-subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
  transition: color var(--transition-normal);
}

.calendar-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);

  @include forTouch {
    width: var(--touch-target);
    height: var(--touch-target);
  }
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast), border-color var(--transition-fast),
    background-color var(--transition-fast);

  &:hover:not(:disabled) {
    color: var(--color-primary);
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &--spinning {
    :deep(svg) {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// Empty state (reuse pattern from bangumi page)
.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 40vh;
  padding: 24px;
}

.empty-guide-header {
  text-align: center;
}

.empty-guide-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
  transition: color var(--transition-normal);
}

.empty-guide-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: color var(--transition-normal);
}

// Animations
.anim-fade-in {
  animation: fadeIn 0.5s ease both;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .anim-fade-in {
    animation: none;
  }
}
</style>
