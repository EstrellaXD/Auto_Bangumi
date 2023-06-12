<script lang="ts" setup>
import type { BangumiRule } from '#/bangumi';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });
const emit = defineEmits<{
  (e: 'apply', rule: BangumiRule): void;
  (e: 'enable', id: number): void;
  (
    e: 'deleteFile',
    type: 'disable' | 'delete',
    opts: { id: number; deleteFile: boolean }
  ): void;
}>();

const show = defineModel('show', { default: false });
const rule = defineModel<BangumiRule>('rule', {
  required: true,
});

const deleteFileDialog = reactive<{
  show: boolean;
  type: 'disable' | 'delete';
}>({
  show: false,
  type: 'disable',
});
watch(show, (val) => {
  if (!val) {
    deleteFileDialog.show = false;
  }
});

function showDeleteFileDialog(type: 'disable' | 'delete') {
  deleteFileDialog.show = true;
  deleteFileDialog.type = type;
}

const close = () => (show.value = false);

function emitdeleteFile(deleteFile: boolean) {
  emit('deleteFile', deleteFileDialog.type, {
    id: rule.value.id,
    deleteFile,
  });
}
function emitApply() {
  emit('apply', rule.value);
}

function emitEnable() {
  emit('enable', rule.value.id);
}

const popupTitle = computed(() => {
  if (rule.value.deleted) {
    return t('homepage.rule.enablerule');
  } else {
    return t('homepage.rule.editrule');
  }
});

const boxSize = computed(() => {
  if (rule.value.deleted) {
    return 'w-300px';
  } else {
    return 'w-380px';
  }
});
</script>

<template>
  <ab-popup v-model:show="show" :title="popupTitle" :css="boxSize">
    <div v-if="rule.deleted">
      <div>{{$t('homepage.rule.enablehit')}}</div>

      <div line my-8px></div>

      <div fx-cer justify-center space-x-10px>
        <ab-button size="small" type="warn" @click="() => emitEnable()"
          >{{$t('homepage.rule.yesbtn')}}</ab-button
        >
        <ab-button size="small" @click="() => close()">{{$t('homepage.rule.nobtn')}}</ab-button>
      </div>
    </div>

    <div v-else space-y-12px>
      <ab-rule v-model:rule="rule"></ab-rule>

      <div fx-cer justify-end space-x-10px>
        <ab-button
          size="small"
          type="warn"
          @click="() => showDeleteFileDialog('disable')"
          >{{$t('homepage.rule.disable')}}</ab-button
        >
        <ab-button
          size="small"
          type="warn"
          @click="() => showDeleteFileDialog('delete')"
          >{{$t('homepage.rule.delete')}}</ab-button
        >
        <ab-button size="small" @click="emitApply">{{$t('homepage.rule.apply')}}</ab-button>
      </div>
    </div>

    <ab-popup v-model:show="deleteFileDialog.show" :title="$t('homepage.rule.delete')">
      <div>{{$t('homepage.rule.deletehit')}}</div>
      <div line my-8px></div>

      <div fx-cer justify-center space-x-10px>
        <ab-button size="small" type="warn" @click="() => emitdeleteFile(true)"
          >{{$t('homepage.rule.yesbtn')}}</ab-button
        >
        <ab-button size="small" @click="() => emitdeleteFile(false)"
          >{{$t('homepage.rule.nobtn')}}</ab-button
        >
      </div>
    </ab-popup>
  </ab-popup>
</template>
