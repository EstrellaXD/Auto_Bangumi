<script lang="ts" setup>
import { ImageOff } from '@lucide/vue';
import type { BangumiGroup } from './types';

const props = defineProps<{
  dayKeys: readonly string[];
  groupedByDay: Record<string, BangumiGroup[]>;
  todayIndex: number;
  getDayLabel: (key: string) => string;
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
        class="calendar-section calendar-enter"
        :style="{ '--delay': `${index * 0.03}s` }"
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
            class="calendar-today-mark"
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
              >
              <div v-else class="calendar-row-placeholder">
                <ImageOff :size="16" />
              </div>
            </div>
            <div class="calendar-row-info">
              <div class="calendar-row-title">
                <span class="calendar-row-title-text">{{ group.primary.official_title }}</span>
                <ab-badge
                  v-if="group.rules.length > 1"
                  class="calendar-row-badge"
                  :count="group.rules.length"
                />
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
    border-bottom-color: var(--color-accent);
  }
}

.calendar-section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.3px;
  transition: color var(--transition-normal);

  .calendar-section-header--today & {
    color: var(--color-text);
  }
}

// 今天：accent 方块标记 + 墨色文字（DESIGN：accent 只用于日历的今天）
.calendar-today-mark {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text);

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 2px;
    background: var(--color-accent);
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

  @media (hover: hover) {
    &:hover {
      background: var(--color-surface-2);
    }
  }

  &:active {
    background: var(--color-surface-2);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
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
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  transition: color var(--transition-normal);
}

.calendar-row-title-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.calendar-row-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.calendar-row-badge {
  flex-shrink: 0;
  margin-left: 6px;
}
</style>
