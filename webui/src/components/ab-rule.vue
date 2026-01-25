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
  },
  {
    configKey: 'filter',
    label: () => t('homepage.rule.exclude'),
    type: 'dynamic-tags',
  },
];
</script>

<template>
  <div class="rule-form">
    <ab-setting
      v-for="i in items"
      :key="i.configKey"
      v-bind="i"
      v-model:data="rule[i.configKey]"
    ></ab-setting>

    <!-- Offset field with auto-detect button -->
    <ab-label :label="() => $t('homepage.rule.offset')">
      <div class="offset-controls">
        <input
          v-model.number="rule.offset"
          type="number"
          ab-input
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
    </ab-label>

    <div v-if="offsetReason" class="offset-reason">{{ offsetReason }}</div>
  </div>
</template>

<style lang="scss" scoped>
.rule-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.offset-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;

  @include forTablet {
    width: auto;
    min-width: 220px;
  }

  :deep(.ab-button) {
    flex-shrink: 0;
    white-space: nowrap;
  }
}

.offset-input {
  width: 80px;
  flex-shrink: 0;

  @include forMobile {
    flex: 1;
    min-width: 60px;
  }
}

.offset-reason {
  font-size: 12px;
  color: var(--color-text-secondary);
  padding-left: 2px;
  margin-top: -8px;
}
</style>
