<script lang="ts" setup>
import { computed } from 'vue';
import AbButton from './ab-button.vue';
import AbModal from './ab-modal.vue';
import { useConfirmState } from '@/hooks/useConfirm';

// 全局确认对话框宿主：挂载一次（App.vue），由 useConfirm() 驱动。
const { state, settle, restoreFocus } = useConfirmState();

const show = computed({
  get: () => state.current !== null,
  set: (value: boolean) => {
    if (!value) settle(false);
  },
});
</script>

<template>
  <AbModal
    v-model:show="show"
    size="sm"
    :show-close="false"
    :title="state.current?.title ?? ''"
    @after-leave="restoreFocus"
  >
    <template v-if="state.current?.body" #default>
      <p class="ab-confirm-body">
        {{ state.current.body }}
      </p>
    </template>

    <template #footer>
      <AbButton class="ab-confirm-cancel" size="sm" @click="settle(false)">
        {{ state.current?.cancelText ?? $t('common.cancel') }}
      </AbButton>
      <AbButton
        class="ab-confirm-ok"
        size="sm"
        :variant="state.current?.danger ? 'danger' : 'primary'"
        @click="settle(true)"
      >
        {{ state.current?.confirmText ?? $t('common.confirm') }}
      </AbButton>
    </template>
  </AbModal>
</template>

<style lang="scss" scoped>
.ab-confirm-body {
  margin: 0;
  font-size: 13.5px;
  color: var(--color-text-secondary);
}
</style>
