<script lang="ts" setup>
import AbField from './basic/ab-field.vue';
import AbTagsInput from './basic/ab-tags-input.vue';

defineProps<{
  modelValue: string[];
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: string[]): void;
}>();
</script>

<template>
  <AbField :label="$t('homepage.rule.filter')">
    <div class="filter-tags">
      <AbTagsInput
        :model-value="modelValue"
        :aria-label="$t('homepage.rule.filter')"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </div>
  </AbField>
</template>

<style lang="scss" scoped>
// 与 AbField 里 ab-input / 下拉框同宽，右列左缘对齐
.filter-tags {
  width: 100%;

  @include forTablet {
    width: 200px;
  }
}
</style>
