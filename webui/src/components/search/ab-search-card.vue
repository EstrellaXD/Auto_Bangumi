<script lang="ts" setup>
import { ErrorPicture, Plus } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

const props = defineProps<{
  bangumi: BangumiRule;
}>();

defineEmits(['click']);

const posterSrc = computed(() => resolvePosterUrl(props.bangumi.poster_link));

// Format season display
const seasonDisplay = computed(() => {
  if (props.bangumi.season_raw) {
    return props.bangumi.season_raw;
  }
  return props.bangumi.season ? `S${props.bangumi.season}` : '';
});
</script>

<template>
  <div
    class="search-card"
    role="button"
    tabindex="0"
    :aria-label="`Add ${bangumi.official_title}`"
    @click="$emit('click')"
    @keydown.enter="$emit('click')"
  >
    <!-- Poster -->
    <div class="card-poster">
      <template v-if="bangumi.poster_link">
        <img :src="posterSrc" :alt="bangumi.official_title" loading="lazy" />
      </template>
      <template v-else>
        <div class="card-placeholder">
          <ErrorPicture theme="outline" size="24" />
        </div>
      </template>
    </div>

    <!-- Info -->
    <div class="card-info">
      <h3 class="card-title">{{ bangumi.official_title }}</h3>
      <p v-if="bangumi.title_raw" class="card-subtitle">{{ bangumi.title_raw }}</p>

      <div class="card-tags">
        <span v-if="bangumi.group_name" class="tag tag-group">
          {{ bangumi.group_name }}
        </span>
        <span v-if="bangumi.dpi" class="tag tag-resolution">
          {{ bangumi.dpi }}
        </span>
        <span v-if="bangumi.subtitle" class="tag tag-subtitle">
          {{ bangumi.subtitle }}
        </span>
        <span v-if="seasonDisplay" class="tag tag-season">
          {{ seasonDisplay }}
        </span>
      </div>
    </div>

    <!-- Add button -->
    <div class="card-action">
      <div class="add-btn">
        <Plus theme="outline" size="18" />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.search-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  user-select: none;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    background: var(--color-surface-hover);

    .add-btn {
      background: var(--color-primary);
      color: #fff;
    }
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  &:active {
    transform: scale(0.98);
  }
}

.card-poster {
  width: 60px;
  height: 84px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-hover);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0;
  transition: color var(--transition-normal);
}

.card-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0;
  line-height: 1.4;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.tag {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.tag-group {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.tag-resolution {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);
}

.tag-subtitle {
  background: rgba(249, 115, 22, 0.15);
  color: var(--color-accent);
}

.tag-season {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.card-action {
  flex-shrink: 0;
}

.add-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  transition: all var(--transition-fast);
}
</style>
