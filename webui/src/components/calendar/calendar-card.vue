<script lang="ts" setup>
import { ImageOff, Pin, X } from '@lucide/vue';
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
      @keydown.space.prevent="emit('click')"
    >
      <div class="calendar-card-poster">
        <img
          v-if="group.primary.poster_link"
          :src="posterSrc"
          :alt="group.primary.official_title"
          class="calendar-card-img"
          loading="lazy"
        >
        <div v-else class="calendar-card-placeholder">
          <ImageOff :size="20" />
          <span class="calendar-card-placeholder-title">
            {{ group.primary.official_title }}
          </span>
        </div>
        <div class="calendar-card-overlay">
          <div class="calendar-card-overlay-title">
            {{ group.primary.official_title }}
          </div>
          <div class="calendar-card-overlay-tags">
            <ab-tag :title="`S${group.primary.season}`" type="info" />
            <ab-tag
              v-if="group.primary.group_name"
              :title="group.primary.group_name"
              type="info"
            />
          </div>
        </div>
        <!-- Pin indicator for manually assigned -->
        <div
          v-if="showUnpin && group.primary.weekday_locked"
          class="calendar-card-pin"
        >
          <Pin fill="currentColor" :size="12" />
        </div>
      </div>
    </div>
    <!-- Unpin button：盖在置顶标记上，悬停 / 键盘聚焦时出现 -->
    <ab-icon-button
      v-if="showUnpin && group.primary.weekday_locked"
      class="calendar-unpin-btn"
      size="sm"
      round
      :label="$t('calendar.unpin')"
      @click="emit('unpin', $event)"
    >
      <X :size="12" />
    </ab-icon-button>
    <ab-badge
      v-if="group.rules.length > 1"
      class="group-badge"
      :count="group.rules.length"
    />
  </div>
</template>

<style lang="scss" scoped>
// Card wrapper for badge positioning
.calendar-card-wrapper {
  position: relative;
}

.group-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  z-index: var(--z-dropdown);
  pointer-events: none;
}

.calendar-card {
  cursor: pointer;
  user-select: none;
  border-radius: var(--radius-sm);
  transition: transform var(--transition-fast),
    box-shadow var(--transition-fast);

  @media (hover: hover) {
    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  border-radius: inherit;
  background: var(--color-surface-2);
  box-shadow: inset 0 0 0 1px var(--color-border);
  color: var(--color-text-muted);
  transition: background-color var(--transition-normal);
}

// 无海报时在卡片上直接显示标题，否则卡片只剩一个灰色占位块
.calendar-card-placeholder-title {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-text-secondary);
  text-align: center;
  overflow: hidden;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

// 标题与标签都放在底部，顶部两角留给置顶标记与组数徽标
.calendar-card-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 4px;
  padding: 5px;
  opacity: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  transition: opacity var(--transition-normal);

  @media (hover: hover) {
    .calendar-card:hover & {
      opacity: 1;
    }
  }
}

.calendar-card-overlay-title {
  padding: 0 1px;
  font-size: 11px;
  font-weight: 500;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.calendar-card-overlay-tags {
  display: flex;
  gap: 3px;
  flex-wrap: wrap;

  :deep(.ab-tag) {
    background: var(--color-overlay);
    border-color: rgba(255, 255, 255, 0.4);
    color: var(--color-white);
    font-size: 9px;
    padding: 1px 5px;

    // 海报叠层上的信息 chip 不需要语义色标记
    &::before {
      display: none;
    }
  }
}

// Pin indicator
.calendar-card-pin {
  position: absolute;
  top: 4px;
  left: 4px;
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

// Unpin button：与置顶标记同心，悬停 / 聚焦时盖住它
.calendar-unpin-btn {
  position: absolute;
  top: 1px;
  left: 1px;
  z-index: var(--z-dropdown);
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-sm);
  opacity: 0;
  // 不可见时不可点：触屏没有 hover，点卡片左上角不能静默取消置顶
  pointer-events: none;
  transition: opacity var(--transition-fast),
    background-color var(--transition-fast);

  // 只认键盘焦点：触摸点开卡片后焦点留在卡片上，不应让按钮常显
  .calendar-card-wrapper:has(:focus-visible) & {
    opacity: 1;
    pointer-events: auto;
  }

  @media (hover: hover) {
    .calendar-card-wrapper:hover & {
      opacity: 1;
      pointer-events: auto;
    }
  }
}

// Pinned card subtle styling：用 outline，悬停阴影不会盖掉它
.calendar-card--pinned {
  outline: 1.5px solid var(--color-primary);
}
</style>
