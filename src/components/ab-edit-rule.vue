<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';

const emit = defineEmits<{
  delete: [{ id: number; deleteFile: boolean }];
  apply: [item: BangumiRule];
}>();

const show = defineModel('show', { default: false });
const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const deleteRuleDialog = ref(false);
watch(show, (val) => {
  if (!val) {
    deleteRuleDialog.value = false;
  }
});

function emitDelete(deleteFile: boolean) {
  emit('delete', {
    id: rule.value.id,
    deleteFile,
  });
}
function emitApply() {
  emit('apply', rule.value);
}
</script>

<template>
  <ab-popup v-model:show="show" title="Edit Rule" css="w-380px">
    <div space-y-12px>
      <ab-rule v-model:rule="rule"></ab-rule>

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
        <ab-button size="small" type="warn" @click="() => emitDelete(true)"
          >Yes</ab-button
        >
        <ab-button size="small" @click="() => emitDelete(false)">No</ab-button>
      </div>
    </ab-popup>
  </ab-popup>
</template>
