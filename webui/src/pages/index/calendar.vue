<script lang="ts" setup>
import { ErrorPicture, Refresh } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

definePage({
  name: 'Calendar',
});

const { t } = useMyI18n();
const posterSrc = (link: string | null | undefined) => resolvePosterUrl(link);
const { bangumi } = storeToRefs(useBangumiStore());
const { getAll, openEditPopup } = useBangumiStore();
const { isMobile } = useBreakpointQuery();

const refreshing = ref(false);

async function refreshCalendar() {
  refreshing.value = true;
  try {
    await apiBangumi.refreshCalendar();
    await getAll();
  } finally {
    refreshing.value = false;
  }
}

onActivated(() => {
  refreshCalendar();
});

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

const todayIndex = computed(() => {
  // JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat
  // We want: 0=Mon, 1=Tue, ..., 6=Sun
  const jsDay = new Date().getDay();
  return jsDay === 0 ? 6 : jsDay - 1;
});

const bangumiByDay = computed(() => {
  const groups: Record<string, BangumiRule[]> = {};
  DAY_KEYS.forEach((key) => (groups[key] = []));
  groups['unknown'] = [];

  bangumi.value?.forEach((item) => {
    if (item.deleted) return;
    const weekday = item.air_weekday;
    if (weekday != null && weekday >= 0 && weekday <= 6) {
      groups[DAY_KEYS[weekday]].push(item);
    } else {
      groups['unknown'].push(item);
    }
  });

  return groups;
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

function isToday(index: number): boolean {
  return index === todayIndex.value;
}
</script>

<template>
  <div class="page-calendar">
    <!-- Header -->
    <div class="calendar-header anim-fade-in">
      <div class="calendar-header-text">
        <h2 class="calendar-title">{{ $t('calendar.title') }}</h2>
        <p class="calendar-subtitle">{{ $t('calendar.subtitle') }}</p>
      </div>
      <button
        class="calendar-refresh-btn"
        :class="{ 'calendar-refresh-btn--spinning': refreshing }"
        :disabled="refreshing"
        :title="$t('calendar.refresh')"
        @click="refreshCalendar"
      >
        <Refresh :size="18" />
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="!hasBangumi" class="empty-guide">
      <div class="empty-guide-header anim-fade-in">
        <div class="empty-guide-title">{{ $t('calendar.empty_state.title') }}</div>
        <div class="empty-guide-subtitle">{{ $t('calendar.empty_state.subtitle') }}</div>
      </div>
    </div>

    <!-- Desktop: Grid columns -->
    <div v-else-if="!isMobile" class="calendar-grid">
      <div
        v-for="(key, index) in [...DAY_KEYS, 'unknown']"
        :key="key"
        class="calendar-column anim-slide-up"
        :class="{ 'calendar-column--today': key !== 'unknown' && isToday(index) }"
        :style="{ '--delay': `${index * 0.05}s` }"
      >
        <!-- Day header -->
        <div
          class="calendar-day-header"
          :class="{ 'calendar-day-header--today': key !== 'unknown' && isToday(index) }"
        >
          <span class="calendar-day-label">{{ getDayLabel(key) }}</span>
          <span
            v-if="key !== 'unknown' && isToday(index)"
            class="calendar-today-badge"
          >
            {{ $t('calendar.today') }}
          </span>
        </div>

        <!-- Anime cards -->
        <div class="calendar-column-items">
          <div
            v-for="item in bangumiByDay[key]"
            :key="item.id"
            class="calendar-card"
            role="button"
            tabindex="0"
            :aria-label="`Edit ${item.official_title}`"
            @click="openEditPopup(item)"
            @keydown.enter="openEditPopup(item)"
          >
            <div class="calendar-card-poster">
              <img
                v-if="item.poster_link"
                :src="posterSrc(item.poster_link)"
                :alt="item.official_title"
                class="calendar-card-img"
              />
              <div v-else class="calendar-card-placeholder">
                <ErrorPicture theme="outline" size="20" />
              </div>
              <div class="calendar-card-overlay">
                <div class="calendar-card-overlay-tags">
                  <ab-tag :title="`S${item.season}`" type="primary" />
                  <ab-tag
                    v-if="item.group_name"
                    :title="item.group_name"
                    type="primary"
                  />
                </div>
                <div class="calendar-card-overlay-title">{{ item.official_title }}</div>
              </div>
            </div>
          </div>

          <!-- Empty day -->
          <div v-if="bangumiByDay[key].length === 0" class="calendar-empty-day">
            {{ $t('calendar.empty') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Mobile: Vertical list -->
    <div v-else class="calendar-list">
      <template v-for="(key, index) in [...DAY_KEYS, 'unknown']" :key="key">
        <div
          v-if="bangumiByDay[key].length > 0"
          class="calendar-section anim-slide-up"
          :style="{ '--delay': `${index * 0.05}s` }"
        >
          <!-- Day divider -->
          <div
            class="calendar-section-header"
            :class="{ 'calendar-section-header--today': key !== 'unknown' && isToday(index) }"
          >
            <span class="calendar-section-label">{{ getDayLabel(key) }}</span>
            <span
              v-if="key !== 'unknown' && isToday(index)"
              class="calendar-today-badge calendar-today-badge--small"
            >
              {{ $t('calendar.today') }}
            </span>
          </div>

          <!-- Anime rows -->
          <div class="calendar-section-items">
            <div
              v-for="item in bangumiByDay[key]"
              :key="item.id"
              class="calendar-row"
              role="button"
              tabindex="0"
              :aria-label="`Edit ${item.official_title}`"
              @click="openEditPopup(item)"
              @keydown.enter="openEditPopup(item)"
            >
              <div class="calendar-row-poster">
                <img
                  v-if="item.poster_link"
                  :src="posterSrc(item.poster_link)"
                  :alt="item.official_title"
                  class="calendar-row-img"
                />
                <div v-else class="calendar-row-placeholder">
                  <ErrorPicture theme="outline" size="16" />
                </div>
              </div>
              <div class="calendar-row-info">
                <div class="calendar-row-title">{{ item.official_title }}</div>
                <div class="calendar-row-meta">
                  <ab-tag :title="`S${item.season}`" type="primary" />
                  <ab-tag
                    v-if="item.group_name"
                    :title="item.group_name"
                    type="primary"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- All days empty on mobile -->
      <div v-if="!hasBangumi" class="calendar-empty-day calendar-empty-day--mobile">
        {{ $t('calendar.no_data') }}
      </div>
    </div>

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

.calendar-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  transition: color var(--transition-normal);
}

.calendar-subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0 0;
  transition: color var(--transition-normal);
}

.calendar-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast),
              border-color var(--transition-fast),
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
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// Desktop grid
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
  flex: 1;
}

.calendar-column {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal);

  &--today {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 1px var(--color-primary-light);
  }
}

.calendar-day-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);

  &--today {
    background: var(--color-primary-light);
  }
}

.calendar-day-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: color var(--transition-normal);

  .calendar-day-header--today & {
    color: var(--color-primary);
  }
}

.calendar-today-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-primary-light);
  padding: 1px 6px;
  border-radius: var(--radius-full);

  &--small {
    font-size: 10px;
    padding: 0 5px;
  }
}

.calendar-column-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

// Desktop card
.calendar-card {
  cursor: pointer;
  user-select: none;
  border-radius: var(--radius-md);
  transition: transform var(--transition-fast),
              box-shadow var(--transition-fast);

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.calendar-card-poster {
  position: relative;
  border-radius: var(--radius-sm);
  overflow: hidden;
  aspect-ratio: 2 / 3;
}

.calendar-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.calendar-card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  transition: background-color var(--transition-normal);
}

.calendar-card-overlay {
  position: absolute;
  inset: 0;
  opacity: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  transition: opacity var(--transition-normal);

  .calendar-card:hover & {
    opacity: 1;
  }
}

.calendar-card-overlay-title {
  position: absolute;
  top: 6px;
  left: 6px;
  right: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.calendar-card-overlay-tags {
  position: absolute;
  bottom: 5px;
  left: 5px;
  right: 5px;
  display: flex;
  gap: 3px;
  flex-wrap: wrap;

  :deep(.tag) {
    background: rgba(0, 0, 0, 0.5);
    border-color: rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 9px;
    padding: 1px 5px;
  }
}

// Empty day
.calendar-empty-day {
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: center;
  padding: 12px 4px;
  transition: color var(--transition-normal);

  &--mobile {
    padding: 32px 16px;
    font-size: 14px;
  }
}

// Mobile list
.calendar-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.calendar-section {
  margin-bottom: 8px;
}

.calendar-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0 6px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 6px;
  transition: border-color var(--transition-normal);

  &--today {
    border-bottom-color: var(--color-primary);
  }
}

.calendar-section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  letter-spacing: 0.3px;
  transition: color var(--transition-normal);

  .calendar-section-header--today & {
    color: var(--color-primary);
  }
}

.calendar-section-items {
  display: flex;
  flex-direction: column;
}

.calendar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: var(--radius-md);
  cursor: pointer;
  user-select: none;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }
}

.calendar-row-poster {
  width: 44px;
  height: 62px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
}

.calendar-row-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.calendar-row-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  transition: background-color var(--transition-normal);
}

.calendar-row-info {
  flex: 1;
  min-width: 0;
}

.calendar-row-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
  transition: color var(--transition-normal);
}

.calendar-row-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
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

.anim-slide-up {
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay, 0s);
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

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .anim-fade-in,
  .anim-slide-up {
    animation: none;
  }

  .calendar-card {
    &:hover {
      transform: none;
    }
  }
}
</style>
