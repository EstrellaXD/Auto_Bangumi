<script lang="ts" setup>
import AbButton from '../basic/ab-button.vue';
import AbField from '../basic/ab-field.vue';
import AbInput from '../basic/ab-input.vue';
import AbSelect from '../basic/ab-select.vue';
import AbSwitch from '../basic/ab-switch.vue';
import AbTagsInput from '../basic/ab-tags-input.vue';
import { useConfirm } from '@/hooks/useConfirm';
import { fillSchemaDefaults } from '@/utils/plugin-schema';
import type { SchemaField } from '@/utils/plugin-schema';

// 由插件 config_model 的 JSON Schema 渲染的表单；字段描述由 schemaFields() 生成
defineProps<{ fields: SchemaField[] }>();
const model = defineModel<Record<string, unknown>>({ required: true });
const { t } = useMyI18n();
const { confirm } = useConfirm();

// 行对象 → 稳定 key，删除中间行后其余行的输入框不被复用错位
const rowKeys = new WeakMap<object, number>();
let nextRowKey = 0;
function rowKey(row: object) {
  if (!rowKeys.has(row)) rowKeys.set(row, nextRowKey++);
  return rowKeys.get(row);
}

// 只用 schema 已给出的信息：required 列表与 minimum/maximum
function errorOf(field: SchemaField): string {
  const value = model.value[field.key];
  const empty =
    value === undefined ||
    value === null ||
    value === '' ||
    (Array.isArray(value) && value.length === 0);
  if (field.required && empty) return t('config.plugins_set.field_required');
  if (typeof value !== 'number') return '';
  if (field.minimum !== undefined && value < field.minimum)
    return t('config.plugins_set.field_min', { n: field.minimum });
  if (field.maximum !== undefined && value > field.maximum)
    return t('config.plugins_set.field_max', { n: field.maximum });
  return '';
}

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

// 填过内容的行（与新增时的默认行不同）删除前先确认
async function removeRow(field: SchemaField, index: number) {
  const rows = rowsOf(field);
  const blank = fillSchemaDefaults(field.itemFields, {});
  if (
    JSON.stringify(rows[index]) !== JSON.stringify(blank) &&
    !(await confirm({
      title: t('config.plugins_set.remove_row_confirm_title', {
        field: field.label,
        n: index + 1,
      }),
      body: t('config.plugins_set.remove_row_confirm_body'),
      confirmText: t('config.plugins_set.remove_row'),
      danger: true,
    }))
  )
    return;
  model.value[field.key] = rows.filter((_, i) => i !== index);
}

function setNumber(field: SchemaField, value: string | number) {
  const parsed = Number(value);
  if (value === '' || Number.isNaN(parsed)) {
    // 清空时回到 schema 默认值，没有默认值才删除该键
    if (field.default === undefined || field.default === null)
      delete model.value[field.key];
    else model.value[field.key] = field.default;
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
      :required="field.required"
      :error="errorOf(field)"
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
        :options="
          field.options.map((value) => ({ label: String(value), value }))
        "
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
      <AbTagsInput
        v-else-if="field.kind === 'tags'"
        :model-value="(model[field.key] as string[] | undefined) ?? []"
        :aria-label="field.label"
        @update:model-value="model[field.key] = $event"
      />
      <div v-else-if="field.kind === 'objects'" class="schema-form__rows">
        <div
          v-for="(row, index) in rowsOf(field)"
          :key="rowKey(row)"
          class="schema-form__row"
        >
          <PluginSchemaForm :model-value="row" :fields="field.itemFields" />
          <AbButton
            size="sm"
            variant="ghost"
            :aria-label="
              $t('config.plugins_set.remove_row_n', {
                field: field.label,
                n: index + 1,
              })
            "
            @click="removeRow(field, index)"
          >
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
