<script lang="ts" setup>
import { RefreshCw } from '@lucide/vue';
import type { BangumiRule } from '#/bangumi';
import type { BangumiGroup } from '@/components/calendar/types';

definePage({
  name: 'Calendar',
});

const { activeBangumi } = storeToRefs(useBangumiStore());
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

  activeBangumi.value.forEach((item) => {
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
  return activeBangumi.value.length > 0;
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
    <div class="calendar-header calendar-enter">
      <!-- 页面本身已有 h1 “Calendar”，这里不再重复标题，只留说明文字 -->
      <div class="calendar-header-text">
        <p class="calendar-subtitle">
          {{ $t('calendar.subtitle') }}
        </p>
      </div>
      <ab-icon-button
        :class="{ 'calendar-refresh-btn--spinning': refreshing }"
        :disabled="refreshing"
        :label="$t('calendar.refresh')"
        @click="refreshCalendar"
      >
        <RefreshCw :size="18" />
      </ab-icon-button>
    </div>

    <!-- Empty state -->
    <ab-empty
      v-if="!hasBangumi"
      class="empty-guide calendar-enter"
      :title="$t('calendar.empty_state.title')"
      :description="$t('calendar.empty_state.subtitle')"
    >
      <template #action>
        <ab-button size="sm" :loading="refreshing" @click="refreshCalendar">
          {{ $t('calendar.refresh') }}
        </ab-button>
      </template>
    </ab-empty>

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

.calendar-refresh-btn--spinning :deep(svg) {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

<style lang="scss">
// 日历页统一进场：标题、星期列、移动端分区共用（子组件根元素加 calendar-enter + --delay）
.calendar-enter {
  animation: calendar-enter var(--transition-slow) both;
  animation-delay: var(--delay, 0s);
}

@keyframes calendar-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .calendar-enter {
    animation: none;
  }
}
</style>
