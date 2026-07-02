<script lang="ts" setup>
import { ErrorPicture, Pin } from '@icon-park/vue-next';
import type { BangumiGroup } from './types';

const props = defineProps<{
  group: BangumiGroup;
  /** 是否展示已手动锁定的“取消置顶”按钮（未知播出日分区的卡片不展示） */
  showUnpin?: boolean;
}>();

const emit = defineEmits<{
  (e: 'click'): void;
  (e: 'unpin', event: Event): void;
}>();

const posterSrc = computed(() =>
  resolvePosterUrl(props.group.primary.poster_link)
);
</script>

<template>
  <div class="calendar-card-wrapper">
    <div
      class="calendar-card"
      :class="{
        'calendar-card--pinned': showUnpin && group.primary.weekday_locked,
      }"
      role="button"
      tabindex="0"
      :aria-label="`Edit ${group.primary.official_title}`"
      @click="emit('click')"
      @keydown.enter="emit('click')"
    >
      <div class="calendar-card-poster">
        <img
          v-if="group.primary.poster_link"
          :src="posterSrc"
          :alt="group.primary.official_title"
          class="calendar-card-img"
          loading="lazy"
        />
        <div v-else class="calendar-card-placeholder">
          <ErrorPicture theme="outline" size="20" />
        </div>
        <div class="calendar-card-overlay">
          <div class="calendar-card-overlay-tags">
            <ab-tag :title="`S${group.primary.season}`" type="primary" />
            <ab-tag
              v-if="group.primary.group_name"
              :title="group.primary.group_name"
              type="primary"
            />
          </div>
          <div class="calendar-card-overlay-title">
            {{ group.primary.official_title }}
          </div>
        </div>
        <!-- Pin indicator for manually assigned -->
        <div
          v-if="showUnpin && group.primary.weekday_locked"
          class="calendar-card-pin"
        >
          <Pin theme="filled" size="12" />
        </div>
      </div>
    </div>
    <!-- Unpin button -->
    <button
      v-if="showUnpin && group.primary.weekday_locked"
      class="calendar-unpin-btn"
      :title="$t('calendar.unpin')"
      @click="emit('unpin', $event)"
    >
      &times;
    </button>
    <div v-if="group.rules.length > 1" class="group-badge">
      {{ group.rules.length }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
// Card wrapper for badge positioning
.calendar-card-wrapper {
  position: relative;
}

.group-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 10px;
  background: var(--color-badge-bg);
  color: var(--color-white);
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-dropdown);
  pointer-events: none;
  box-shadow: 0 2px 4px var(--color-badge-shadow);
}

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

// Pin indicator
.calendar-card-pin {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

// Unpin button
.calendar-unpin-btn {
  position: absolute;
  top: -6px;
  left: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-danger, #e74c3c);
  color: #fff;
  border: none;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-dropdown);
  opacity: 0;
  transition: opacity var(--transition-fast);

  .calendar-card-wrapper:hover & {
    opacity: 1;
  }
}

// Pinned card subtle styling
.calendar-card--pinned {
  box-shadow: 0 0 0 1.5px var(--color-primary);
  border-radius: var(--radius-md);
}
</style>
