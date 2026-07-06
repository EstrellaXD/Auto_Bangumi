<script lang="ts" setup>
import type { BangumiGroup } from './types';
import type { BangumiRule } from '#/bangumi';

defineProps<{
  group: BangumiGroup | null;
}>();

const emit = defineEmits<{
  (e: 'select', rule: BangumiRule): void;
}>();

const show = defineModel<boolean>('show', { default: false });
</script>

<template>
  <ab-modal v-model:show="show" :title="group?.primary.official_title || ''">
    <div v-if="group" class="rule-list">
      <div class="rule-list-hint">{{ $t('homepage.rule.select_hint') }}</div>
      <div
        v-for="rule in group.rules"
        :key="rule.id"
        class="rule-list-item"
        :class="[rule.deleted && 'rule-list-item--disabled']"
        role="button"
        tabindex="0"
        @click="emit('select', rule)"
        @keydown.enter="emit('select', rule)"
        @keydown.space.prevent="emit('select', rule)"
      >
        <div class="rule-list-item-info">
          <div class="rule-list-item-title">
            {{
              rule.group_name || rule.rule_name || $t('homepage.rule.unnamed')
            }}
          </div>
          <div class="rule-list-item-tags">
            <ab-tag v-if="rule.dpi" :title="rule.dpi" type="info" />
            <ab-tag
              v-if="rule.subtitle"
              :title="rule.subtitle"
              type="info"
            />
            <ab-tag v-if="rule.source" :title="rule.source" type="info" />
          </div>
          <div
            v-if="rule.filter && rule.filter.length > 0"
            class="rule-list-item-filter"
          >
            <span class="rule-list-item-filter-label"
              >{{ $t('homepage.rule.filter') }}:</span
            >
            <span class="rule-list-item-filter-value">{{
              rule.filter.join(', ')
            }}</span>
          </div>
          <div v-if="rule.title_raw" class="rule-list-item-raw">
            {{ rule.title_raw }}
          </div>
        </div>
        <div class="rule-list-item-arrow">&rsaquo;</div>
      </div>
    </div>
  </ab-modal>
</template>

<style lang="scss" scoped>
.rule-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  min-width: 300px;
}

.rule-list-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 4px 12px 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 4px;
}

.rule-list-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-height: var(--touch-target);
  padding: 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);

  &:hover {
    background: var(--color-surface-hover);
  }

  &:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  &--disabled {
    opacity: 0.5;
  }
}

.rule-list-item-info {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.rule-list-item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-list-item-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.rule-list-item-filter {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-list-item-filter-label {
  color: var(--color-text-secondary);
}

.rule-list-item-filter-value {
  font-family: var(--font-mono, monospace);
}

.rule-list-item-raw {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-style: italic;
}

.rule-list-item-arrow {
  font-size: 18px;
  color: var(--color-text-muted);
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
