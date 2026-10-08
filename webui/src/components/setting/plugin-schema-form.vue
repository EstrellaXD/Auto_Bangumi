<script lang="ts" setup>
import { NDynamicTags } from 'naive-ui';
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbInput from '../basic/ab-input.vue';
import AbSelect from '../basic/ab-select.vue';
import AbSwitch from '../basic/ab-switch.vue';
import { fillSchemaDefaults } from '@/utils/plugin-schema';
import type { SchemaField } from '@/utils/plugin-schema';

// 由插件 config_model 的 JSON Schema 渲染的表单；字段描述由 schemaFields() 生成
defineProps<{ fields: SchemaField[] }>();
const model = defineModel<Record<string, unknown>>({ required: true });

function rowsOf(field: SchemaField): Record<string, unknown>[] {
  return (
    (model.value[field.key] as Record<string, unknown>[] | undefined) ?? []
  );
}

function addRow(field: SchemaField) {
  model.value[field.key] = [
    ...rowsOf(field),
    fillSchemaDefaults(field.itemFields, {}),
  ];
}

function removeRow(field: SchemaField, index: number) {
  model.value[field.key] = rowsOf(field).filter((_, i) => i !== index);
}

function setNumber(field: SchemaField, value: string | number) {
  const parsed = Number(value);
  if (value === '' || Number.isNaN(parsed)) {
    delete model.value[field.key];
    return;
  }
  model.value[field.key] = field.integer ? Math.trunc(parsed) : parsed;
}
</script>

<template>
  <div class="schema-form">
    <AbField
      v-for="field in fields"
      :key="field.key"
      :label="field.label"
      :description="field.description"
    >
      <AbSwitch
        v-if="field.kind === 'switch'"
        :model-value="Boolean(model[field.key])"
        :aria-label="field.label"
        @update:model-value="model[field.key] = $event"
      />
      <AbSelect
        v-else-if="field.kind === 'select'"
        :model-value="(model[field.key] as string | number | null) ?? null"
        :items="field.options.map(String)"
        :aria-label="field.label"
        @update:model-value="model[field.key] = $event"
      />
      <AbInput
        v-else-if="field.kind === 'number'"
        type="number"
        :model-value="(model[field.key] as number | undefined) ?? ''"
        :aria-label="field.label"
        @update:model-value="setNumber(field, $event)"
      />
      <NDynamicTags
        v-else-if="field.kind === 'tags'"
        :value="(model[field.key] as string[] | undefined) ?? []"
        size="small"
        @update:value="model[field.key] = $event"
      />
      <div v-else-if="field.kind === 'objects'" class="schema-form__rows">
        <div
          v-for="(row, index) in rowsOf(field)"
          :key="index"
          class="schema-form__row"
        >
          <PluginSchemaForm :model-value="row" :fields="field.itemFields" />
          <AbButton size="sm" variant="ghost" @click="removeRow(field, index)">
            {{ $t('config.plugins_set.remove_row') }}
          </AbButton>
        </div>
        <AbButton size="sm" class="schema-form__add" @click="addRow(field)">
          {{ $t('config.plugins_set.add_row') }}
        </AbButton>
      </div>
      <AbInput
        v-else-if="field.kind === 'text' || field.kind === 'password'"
        :type="field.kind === 'password' ? 'password' : 'text'"
        :autocomplete="field.kind === 'password' ? 'off' : undefined"
        :model-value="(model[field.key] as string | undefined) ?? ''"
        :aria-label="field.label"
        @update:model-value="model[field.key] = $event"
      />
      <span v-else class="schema-form__unsupported">
        {{ $t('config.plugins_set.unsupported_field') }}
      </span>
    </AbField>
  </div>
</template>

<style lang="scss" scoped>
.schema-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.schema-form__rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.schema-form__row {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.schema-form__add {
  align-self: flex-start;
}

.schema-form__unsupported {
  color: var(--color-text-secondary);
  font-size: 12px;
}
</style>
