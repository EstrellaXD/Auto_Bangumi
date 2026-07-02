<script lang="ts" setup>
import draggable from 'vuedraggable';
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

const { setWeekday } = useBangumiStore();

const isDragging = ref(false);

function isToday(index: number): boolean {
  return index === props.todayIndex;
}

async function onDropToDay(dayIndex: number, evt: any) {
  if (evt.added) {
    const group: BangumiGroup = evt.added.element;
    for (const rule of group.rules) {
      await setWeekday(rule.id, dayIndex);
    }
  }
}

async function onUnpin(group: BangumiGroup, event: Event) {
  event.stopPropagation();
  for (const rule of group.rules) {
    await setWeekday(rule.id, null);
  }
}

const unknownGroups = computed({
  get: () => props.groupedByDay.unknown || [],
  set: () => {
    // No-op: actual update happens via API in onDropToDay
  },
});
</script>

<template>
  <div class="calendar-desktop">
    <div class="calendar-grid">
      <calendar-day-column
        v-for="(key, index) in dayKeys"
        :key="key"
        :day-label="getDayLabel(key)"
        :is-today="isToday(index)"
        :is-dragging="isDragging"
        :groups="groupedByDay[key] || []"
        :delay="`${index * 0.05}s`"
        @change="onDropToDay(index, $event)"
        @card-click="emit('card-click', $event)"
        @unpin="(group, event) => onUnpin(group, event)"
      />
    </div>

    <!-- Unknown air day section (draggable source) -->
    <div
      v-if="unknownGroups.length > 0"
      class="calendar-unknown-section anim-slide-up"
      style="--delay: 0.4s"
    >
      <div class="calendar-unknown-header">
        <span class="calendar-day-label">{{ getDayLabel('unknown') }}</span>
        <span class="calendar-drag-hint">{{ $t('calendar.drag_hint') }}</span>
      </div>
      <draggable
        v-model="unknownGroups"
        :group="{ name: 'calendar', pull: 'clone', put: false }"
        item-key="key"
        :sort="false"
        ghost-class="sortable-ghost"
        drag-class="sortable-drag"
        class="calendar-unknown-items"
        @start="isDragging = true"
        @end="isDragging = false"
      >
        <template #item="{ element: group }">
          <calendar-card :group="group" @click="emit('card-click', group)" />
        </template>
      </draggable>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.calendar-desktop {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}

.calendar-unknown-section {
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 12px;
}

.calendar-unknown-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  margin-bottom: 10px;
}

.calendar-unknown-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}

.calendar-day-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: color var(--transition-normal);
}

.calendar-drag-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  font-style: italic;
}

.sortable-ghost {
  opacity: 0.4;
}

.sortable-drag {
  opacity: 0.9;
  box-shadow: var(--shadow-lg);
  transform: rotate(2deg);
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
