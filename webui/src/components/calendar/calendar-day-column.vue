<script lang="ts" setup>
import draggable from 'vuedraggable';
import type { BangumiGroup } from './types';

const props = defineProps<{
  dayLabel: string;
  isToday: boolean;
  isDragging: boolean;
  groups: BangumiGroup[];
  delay: string;
}>();

const emit = defineEmits<{
  (e: 'change', evt: any): void;
  (e: 'card-click', group: BangumiGroup): void;
  (e: 'unpin', group: BangumiGroup, event: Event): void;
}>();
</script>

<template>
  <div
    class="calendar-column anim-slide-up"
    :class="{
      'calendar-column--today': isToday,
      'calendar-column--drop-active': isDragging,
    }"
    :style="{ '--delay': delay }"
  >
    <!-- Day header -->
    <div
      class="calendar-day-header"
      :class="{ 'calendar-day-header--today': isToday }"
    >
      <span class="calendar-day-label">{{ dayLabel }}</span>
      <span v-if="isToday" class="calendar-today-badge">{{
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
    border-color: var(--color-primary);
    box-shadow: 0 0 0 1px var(--color-primary-light);
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
