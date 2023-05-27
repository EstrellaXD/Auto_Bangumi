<script lang="ts" setup>
import type { AbEditRule, SettingItem } from '#/components';

const emit = defineEmits<{
  delete: [{ id: number; deleteFile: boolean }];
  apply: [item: AbEditRule];
}>();

const show = defineModel('show', { default: false });
const item = defineModel<AbEditRule>('item', {
  default: () => {
    return {
      id: -1,
      official_title: '',
      year: '',
      season: 1,
      offset: 0,
      filter: [],
    };
  },
});

const deleteRuleDialog = ref(false);
watch(show, (val) => {
  if (!val) {
    deleteRuleDialog.value = false;
  }
});

function emitDelete(deleteFile: boolean) {
  emit('delete', {
    id: item.value.id,
    deleteFile,
  });
}
function emitApply() {
  emit('apply', item.value);
}

const items: SettingItem<AbEditRule>[] = [
  {
    configKey: 'official_title',
    label: 'Officical Ttile',
    type: 'input',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'year',
    label: 'Year',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'text',
    },
  },
  {
    configKey: 'season',
    label: 'Season',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
    bottomLine: true,
  },
  {
    configKey: 'offset',
    label: 'Offset',
    type: 'input',
    css: 'w-72px',
    prop: {
      type: 'number',
    },
  },
  {
    configKey: 'filter',
    label: 'Exclude',
    type: 'dynamic-tags',
    bottomLine: true,
  },
];
</script>

<template>
  <ab-popup v-model:show="show" title="Edit Rule" css="w-380px">
    <div space-y-12px>
      <ab-setting
        v-for="i in items"
        :key="i.configKey"
        v-bind="i"
        v-model:data="item[i.configKey]"
      ></ab-setting>

      <div fx-cer justify-end space-x-10px>
        <ab-button
          size="small"
          type="warn"
          @click="() => (deleteRuleDialog = true)"
          >Delete</ab-button
        >
        <ab-button size="small" @click="emitApply">Apply</ab-button>
      </div>
    </div>

    <ab-popup v-model:show="deleteRuleDialog" title="Delete">
      <div>Delete Local File?</div>
      <div line my-8px></div>

      <div fx-cer justify-center space-x-10px>
        <ab-button size="small" type="warn" @click="emitDelete(true)"
          >Yes</ab-button
        >
        <ab-button size="small" @click="emitDelete(false)">No</ab-button>
      </div>
    </ab-popup>
  </ab-popup>
</template>
