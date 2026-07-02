<script lang="ts" setup>
import { ErrorPicture } from '@icon-park/vue-next';
import type { BangumiRule } from '#/bangumi';

/**
 * ab-add-rss / ab-edit-rule 共用的番剧预览区块：海报 + 可编辑的标题/年份/季度。
 * 通过 v-model:rule 双向绑定，避免直接修改 props。
 */
defineProps<{
  posterSrc: string;
}>();

const rule = defineModel<BangumiRule>('rule', { required: true });
</script>

<template>
  <div class="bangumi-info">
    <div class="bangumi-poster">
      <template v-if="rule.poster_link">
        <img :src="posterSrc" :alt="rule.official_title" />
      </template>
      <template v-else>
        <div class="poster-placeholder">
          <ErrorPicture theme="outline" size="32" />
        </div>
      </template>
    </div>
    <div class="bangumi-meta">
      <input
        v-model="rule.official_title"
        type="text"
        class="title-input"
        :placeholder="$t('homepage.rule.official_title')"
      />
      <p v-if="rule.title_raw" class="bangumi-subtitle">{{ rule.title_raw }}</p>
      <div class="meta-row">
        <input
          :value="rule.year ?? ''"
          type="text"
          class="year-input"
          :class="{ 'year-input--empty': !rule.year }"
          :placeholder="$t('homepage.rule.year')"
          @input="(e) => (rule.year = (e.target as HTMLInputElement).value || null)"
        />
        <span class="meta-separator">·</span>
        <label class="season-label">S</label>
        <input
          v-model.number="rule.season"
          type="number"
          class="season-input"
          min="1"
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.bangumi-info {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.bangumi-poster {
  width: 80px;
  height: 112px;
  flex-shrink: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface-hover);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.poster-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.bangumi-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title-input {
  width: 100%;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 4px 0;
  outline: none;
  transition: border-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::placeholder {
    color: var(--color-text-muted);
    font-weight: 400;
  }
}

.bangumi-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.year-input {
  width: 60px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  outline: none;
  transition: border-color var(--transition-fast),
    background-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::placeholder {
    color: var(--color-text-muted);
  }

  &--empty {
    background: color-mix(in srgb, var(--color-warning) 15%, transparent);
    border-bottom-color: var(--color-warning);
    border-radius: var(--radius-xs) var(--radius-xs) 0 0;
    padding: 2px 4px;

    &::placeholder {
      color: var(--color-warning);
    }
  }
}

.meta-separator {
  color: var(--color-text-muted);
}

.season-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.season-input {
  width: 40px;
  font-size: 13px;
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 2px 0;
  outline: none;
  text-align: center;
  transition: border-color var(--transition-fast);

  &:hover,
  &:focus {
    border-bottom-color: var(--color-border);
  }

  &:focus {
    border-bottom-color: var(--color-primary);
  }

  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  -moz-appearance: textfield;
}
</style>
