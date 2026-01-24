<script lang="ts" setup>
import { ErrorPicture, Write } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'search' | 'mobile';
    bangumi: BangumiRule;
  }>(),
  {
    type: 'primary',
  }
);

defineEmits(['click']);

const posterSrc = computed(() => resolvePosterUrl(props.bangumi.poster_link));
</script>

<template>
  <!-- Grid poster card -->
  <div
    v-if="type === 'primary'"
    class="card"
    role="button"
    tabindex="0"
    :aria-label="`Edit ${bangumi.official_title}`"
    @click="() => $emit('click')"
    @keydown.enter="() => $emit('click')"
  >
    <div class="card-poster">
      <template v-if="bangumi.poster_link">
        <img :src="posterSrc" :alt="bangumi.official_title" class="card-img" />
      </template>
      <template v-else>
        <div class="card-placeholder">
          <ErrorPicture theme="outline" size="24" />
        </div>
      </template>

      <div class="card-overlay">
        <div class="card-overlay-tags">
          <ab-tag :title="`Season ${bangumi.season}`" type="primary" />
          <ab-tag
            v-if="bangumi.group_name"
            :title="bangumi.group_name"
            type="primary"
          />
        </div>
        <div class="card-edit-btn">
          <Write size="18" />
        </div>
      </div>
    </div>

    <div class="card-info">
      <div class="card-title">{{ bangumi.official_title }}</div>
    </div>
  </div>

  <!-- Search result card -->
  <div v-else-if="type === 'search'" class="search-card">
    <div class="search-card-inner">
      <div class="search-card-content">
        <div class="search-card-thumb">
          <template v-if="bangumi.poster_link">
            <img :src="posterSrc" :alt="bangumi.official_title" class="search-card-img" />
          </template>
          <template v-else>
            <div class="card-placeholder card-placeholder--small">
              <ErrorPicture theme="outline" size="20" />
            </div>
          </template>
        </div>
        <div class="search-card-meta">
          <div class="search-card-title">{{ bangumi.official_title }}</div>
          <div class="card-tags">
            <ab-tag
              v-if="bangumi.season"
              :title="`Season ${bangumi.season}`"
              type="primary"
            />
            <ab-tag
              v-if="bangumi.group_name"
              :title="bangumi.group_name"
              type="primary"
            />
            <ab-tag
              v-if="bangumi.subtitle"
              :title="bangumi.subtitle"
              type="primary"
            />
          </div>
        </div>
      </div>
      <ab-add :round="true" type="medium" @click="() => $emit('click')" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
// Grid poster card
.card {
  width: 150px;
  cursor: pointer;
  user-select: none;
}

.card-poster {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  transition: box-shadow var(--transition-fast), transform var(--transition-fast);

  .card:hover & {
    box-shadow: var(--shadow-lg);
    transform: translateY(-2px);
  }
}

.card-img {
  width: 100%;
  height: 210px;
  object-fit: cover;
  display: block;
}

.card-placeholder {
  width: 100%;
  height: 210px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  transition: background-color var(--transition-normal);

  &--small {
    height: 44px;
  }
}

.card-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  transition: opacity var(--transition-normal);

  .card:hover & {
    opacity: 1;
  }

  .card:active & {
    background: rgba(0, 0, 0, 0.5);
  }
}

.card-overlay-tags {
  position: absolute;
  bottom: 6px;
  left: 6px;
  right: 6px;
  display: flex;
  gap: 3px;
  flex-wrap: wrap;

  :deep(.tag) {
    background: rgba(0, 0, 0, 0.5);
    border-color: rgba(255, 255, 255, 0.4);
    color: #fff;
    font-size: 9px;
    padding: 1px 6px;
  }
}

.card-edit-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-fast);

  .card:active & {
    transform: scale(0.9);
  }
}

.card-info {
  padding: 8px 2px 4px;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--transition-normal);
}

.card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

// Search result card
.search-card {
  width: 480px;
  border-radius: var(--radius-lg);
  padding: 4px;
  background: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
  transition: background-color var(--transition-normal);
}

.search-card-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 12px;
  transition: background-color var(--transition-normal);
}

.search-card-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.search-card-thumb {
  width: 72px;
  height: 44px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
}

.search-card-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.search-card-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.search-card-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
