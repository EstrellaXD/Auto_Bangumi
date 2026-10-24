<script lang="ts" setup>
import { inject } from 'vue';
import { NSwitch } from 'naive-ui';
import { abFieldInjectionKey } from './ab-field.vue';

// NSwitch 的统一封装：尺寸、loading 与 aria 接线在这里定一次。
const { size = 'medium', disabled = false, loading = false } = defineProps<{
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  ariaLabel?: string;
}>();

const model = defineModel<boolean>({ default: false });

const field = inject(abFieldInjectionKey, null);
</script>

<template>
  <NSwitch
    v-model:value="model"
    :size="size"
    :disabled="disabled"
    :loading="loading"
    :aria-label="ariaLabel"
    :aria-labelledby="field?.labelId"
  />
</template>
