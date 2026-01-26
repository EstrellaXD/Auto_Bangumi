<script lang="ts" setup>
import { ErrorPicture } from '@icon-park/vue-next';
import type { GroupedBangumi } from '@/store/search';

const props = defineProps<{
  group: GroupedBangumi;
}>();

const emit = defineEmits<{
  (e: 'select', group: GroupedBangumi): void;
}>();

const posterSrc = computed(() => resolvePosterUrl(props.group.poster_link));

// Count of variants
const variantCount = computed(() => props.group.variants.length);
</script>

<template>
  <div
    class="search-card"
    role="button"
    tabindex="0"
    :aria-label="`View ${group.official_title}`"
    @click="emit('select', group)"
    @keydown.enter="emit('select', group)"
  >
    <!-- Poster -->
    <div class="card-poster">
      <template v-if="group.poster_link">
        <img :src="posterSrc" :alt="group.official_title" loading="lazy" />
      </template>
      <template v-else>
        <div class="card-placeholder">
          <ErrorPicture theme="outline" size="32" />
        </div>
      </template>
      <!-- Variant count badge -->
      <div v-if="variantCount > 1" class="variant-badge">
        {{ variantCount }}
      </div>
    </div>

    <!-- Info -->
    <div class="card-info">
      <h3 class="card-title">{{ group.official_title }}</h3>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.search-card {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  user-select: none;
  overflow: hidden;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary);
    box-shadow: var(--shadow-md);

    .select-btn {
      background: var(--color-primary);
      color: #fff;
    }

    .card-poster img {
      transform: scale(1.03);
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
  position: relative;
  width: 100%;
  aspect-ratio: 5 / 7;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--color-surface-hover);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform var(--transition-normal);
  }
}

.card-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.variant-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-md);
}

.card-info {
  padding: 10px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  margin: 0;
  transition: color var(--transition-normal);
}
</style>
