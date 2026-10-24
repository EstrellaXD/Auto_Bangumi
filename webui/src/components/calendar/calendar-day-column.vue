<script lang="ts" setup>
import draggable from 'vuedraggable';
import type { BangumiGroup } from './types';

const props = defineProps<{
  dayLabel: string;
  isToday: boolean;
  isDragging: boolean;
  groups: BangumiGroup[];
}>();

const emit = defineEmits<{
  (e: 'change', evt: any): void;
  (e: 'card-click', group: BangumiGroup): void;
  (e: 'unpin', group: BangumiGroup, event: Event): void;
}>();
</script>

<template>
  <div
    class="calendar-column"
    :class="{
      'calendar-column--today': isToday,
      'calendar-column--drop-active': isDragging,
    }"
  >
    <!-- Day header -->
    <div class="calendar-day-header">
      <span class="calendar-day-label">{{ dayLabel }}</span>
      <span v-if="isToday" class="calendar-today-mark">{{
        $t('calendar.today')
      }}</span>
    </div>

    <!-- Anime cards (grouped) - drop target -->
    <draggable
      :model-value="props.groups"
      group="calendar"
      item-key="key"
      :sort="false"
      ghost-class="sortable-ghost"
      drag-class="sortable-drag"
      class="calendar-column-items"
      @change="emit('change', $event)"
    >
      <template #item="{ element: group }">
        <calendar-card
          :group="group"
          show-unpin
          @click="emit('card-click', group)"
          @unpin="emit('unpin', group, $event)"
        />
      </template>

      <template #footer>
        <div v-if="props.groups.length === 0" class="calendar-empty-day">
          {{ isDragging ? $t('calendar.drop_here') : $t('calendar.empty') }}
        </div>
      </template>
    </draggable>
  </div>
</template>

<style lang="scss" scoped>
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
    border-color: var(--color-accent);
  }

  &--drop-active {
    border-color: var(--color-primary);
    border-style: dashed;
    background: var(--color-primary-light);
  }
}

.calendar-day-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  container-type: inline-size;
}

.calendar-day-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  white-space: nowrap;
  transition: color var(--transition-normal);

  .calendar-column--today & {
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
  white-space: nowrap;

  // 窄列（平板看板）只留方块；文字仍在 DOM 中供读屏
  @container (max-width: 80px) {
    font-size: 0;
    gap: 0;
  }

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 2px;
    background: var(--color-accent);
  }
}

.calendar-column-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

// vuedraggable ghost and drag classes
.sortable-ghost {
  opacity: 0.4;
}

.sortable-drag {
  opacity: 0.9;
  box-shadow: var(--shadow-lg);
  transform: rotate(2deg);
}

.calendar-empty-day {
  font-size: 12px;
  color: var(--color-text-muted);
  text-align: center;
  padding: 12px 4px;
  transition: color var(--transition-normal);
}
</style>
