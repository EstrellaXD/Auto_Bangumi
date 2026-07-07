<script lang="ts" setup>
import { ErrorPicture } from '@icon-park/vue-next';
import type { BangumiGroup } from './types';

const props = defineProps<{
  dayKeys: readonly string[];
  groupedByDay: Record<string, BangumiGroup[]>;
  todayIndex: number;
  getDayLabel: (key: string) => string;
  hasBangumi: boolean;
}>();

const emit = defineEmits<{
  (e: 'card-click', group: BangumiGroup): void;
}>();

function isToday(index: number): boolean {
  return index === props.todayIndex;
}

function posterSrc(link: string | null | undefined): string {
  return resolvePosterUrl(link);
}
</script>

<template>
  <div class="calendar-list">
    <template v-for="(key, index) in dayKeys" :key="key">
      <div
        v-if="groupedByDay[key].length > 0"
        class="calendar-section anim-slide-up"
        :style="{ '--delay': `${index * 0.05}s` }"
      >
        <!-- Day divider -->
        <div
          class="calendar-section-header"
          :class="{
            'calendar-section-header--today':
              key !== 'unknown' && isToday(index),
          }"
        >
          <span class="calendar-section-label">{{ getDayLabel(key) }}</span>
          <span
            v-if="key !== 'unknown' && isToday(index)"
            class="calendar-today-badge calendar-today-badge--small"
          >
            {{ $t('calendar.today') }}
          </span>
        </div>

        <!-- Anime rows (grouped) -->
        <div class="calendar-section-items">
          <div
            v-for="group in groupedByDay[key]"
            :key="group.key"
            class="calendar-row"
            role="button"
            tabindex="0"
            :aria-label="`Edit ${group.primary.official_title}`"
            @click="emit('card-click', group)"
            @keydown.enter="emit('card-click', group)"
            @keydown.space.prevent="emit('card-click', group)"
          >
            <div class="calendar-row-poster">
              <img
                v-if="group.primary.poster_link"
                :src="posterSrc(group.primary.poster_link)"
                :alt="group.primary.official_title"
                class="calendar-row-img"
                loading="lazy"
              />
              <div v-else class="calendar-row-placeholder">
                <ErrorPicture theme="outline" size="16" />
              </div>
            </div>
            <div class="calendar-row-info">
              <div class="calendar-row-title">
                {{ group.primary.official_title }}
                <span v-if="group.rules.length > 1" class="calendar-row-badge">
                  {{ group.rules.length }}
                </span>
              </div>
              <div class="calendar-row-meta">
                <ab-tag :title="`S${group.primary.season}`" type="info" />
                <ab-tag
                  v-if="group.primary.group_name"
                  :title="group.primary.group_name"
                  type="info"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- All days empty on mobile -->
    <div
      v-if="!hasBangumi"
      class="calendar-empty-day calendar-empty-day--mobile"
    >
      {{ $t('calendar.no_data') }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
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

.calendar-row-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  margin-left: 6px;
  border-radius: 9px;
  background: var(--color-badge-bg);
  color: var(--color-white);
  font-size: 11px;
  font-weight: 600;
  vertical-align: middle;
}

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

.anim-slide-up {
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay, 0s);
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
  .anim-slide-up {
    animation: none;
  }
}
</style>
