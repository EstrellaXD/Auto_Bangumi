<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import type { SettingItem } from '#/components';

const { t } = useMyI18n();

const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const offsetLoading = ref(false);
const offsetReason = ref('');

async function autoDetectOffset() {
  if (!rule.value.id) return;
  offsetLoading.value = true;
  offsetReason.value = '';
  try {
    const result = await apiBangumi.suggestOffset(rule.value.id);
    rule.value.offset = result.suggested_offset;
    offsetReason.value = result.reason;
  } catch (e) {
    console.error('Failed to detect offset:', e);
  } finally {
    offsetLoading.value = false;
  }
}

const items: SettingItem<BangumiRule>[] = [
  {
    configKey: 'official_title',
    label: () => t('homepage.rule.official_title'),
    type: 'input',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'year',
    label: () => t('homepage.rule.year'),
    type: 'input',
    css: 'w-72',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'season',
    label: () => t('homepage.rule.season'),
    type: 'input',
    css: 'w-72',
    prop: {
      type: 'number',
    },
    bottomLine: true,
  },
  {
    configKey: 'filter',
    label: () => t('homepage.rule.exclude'),
    type: 'dynamic-tags',
    bottomLine: true,
  },
];
</script>

<template>
  <div space-y-12>
    <ab-setting
      v-for="i in items"
      :key="i.configKey"
      v-bind="i"
      v-model:data="rule[i.configKey]"
    ></ab-setting>

    <!-- Offset field with auto-detect button -->
    <div class="offset-row">
      <div class="offset-label">{{ $t('homepage.rule.offset') }}</div>
      <div class="offset-controls">
        <input
          v-model.number="rule.offset"
          type="number"
          class="offset-input"
        />
        <ab-button
          size="small"
          :loading="offsetLoading"
          @click="autoDetectOffset"
        >
          {{ $t('homepage.rule.auto_detect') }}
        </ab-button>
      </div>
      <div v-if="offsetReason" class="offset-reason">{{ offsetReason }}</div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.offset-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.offset-label {
  font-size: 14px;
  color: var(--color-text);
}

.offset-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.offset-input {
  width: 72px;
  padding: 6px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 14px;
  outline: none;
  transition: border-color var(--transition-fast);

  &:focus {
    border-color: var(--color-primary);
  }
}

.offset-reason {
  font-size: 12px;
  color: var(--color-text-secondary);
}
</style>
