<script lang="ts" setup>
import { inject } from 'vue';
import { NSwitch } from 'naive-ui';
import { abFieldInjectionKey } from './ab-field.vue';

// NSwitch 的统一封装：尺寸、loading 与 aria 接线在这里定一次。
withDefaults(
  defineProps<{
    size?: 'small' | 'medium' | 'large';
    disabled?: boolean;
    loading?: boolean;
    ariaLabel?: string;
  }>(),
  {
    size: 'medium',
    disabled: false,
    loading: false,
    ariaLabel: undefined,
  }
);

const model = defineModel<boolean>({ default: false });

const field = inject(abFieldInjectionKey, null);
</script>

<template>
  <NSwitch
    v-model:value="model"
    class="ab-switch"
    :size="size"
    :disabled="disabled"
    :loading="loading"
    :aria-label="ariaLabel"
    :aria-labelledby="field?.labelId"
  ></NSwitch>
</template>

<style lang="scss" scoped>
@media screen and (max-width: 639px) {
  .ab-switch {
    min-width: var(--touch-target);
    min-height: var(--touch-target);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
