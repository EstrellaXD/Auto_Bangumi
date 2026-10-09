<script lang="ts" setup>
import AbInput from './ab-input.vue';
import AbTag from './ab-tag.vue';

// 字符串列表输入：已有项显示为可删除的 ab-tag，回车添加新项（去重、去空白）
defineProps<{ ariaLabel?: string }>();
const model = defineModel<string[]>({ default: () => [] });
const draft = ref('');

function add() {
  const value = draft.value.trim();
  if (value && !model.value.includes(value))
    model.value = [...model.value, value];
  draft.value = '';
}
</script>

<template>
  <div class="ab-tags-input">
    <div v-if="model.length" class="ab-tags-input__list">
      <AbTag
        v-for="tag in model"
        :key="tag"
        closable
        @close="model = model.filter((t) => t !== tag)"
      >
        {{ tag }}
      </AbTag>
    </div>
    <AbInput
      v-model="draft"
      :aria-label="ariaLabel"
      @keydown.enter.prevent="add"
      @blur="add"
    />
  </div>
</template>

<style lang="scss" scoped>
.ab-tags-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.ab-tags-input__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
