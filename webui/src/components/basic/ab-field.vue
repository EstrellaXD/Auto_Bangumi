<script lang="ts">
import { computed, provide, ref, useId } from 'vue';
import type { ComputedRef, InjectionKey, Ref } from 'vue';

export interface AbFieldContext {
  /** 原生控件应设置的 id（配合 <label for>） */
  controlId: string;
  /** 消费 controlId 的控件置 true —— 只有这时才渲染真正的 <label for> */
  adopted: Ref<boolean>;
  /** 标签文本节点 id（无法用 for 关联的组件用 aria-labelledby） */
  labelId: string;
  /** description/error 节点 id 列表，控件应设为 aria-describedby */
  describedBy: ComputedRef<string | undefined>;
  /** 当前是否处于错误态（控件应设 aria-invalid 并显示错误样式） */
  invalid: ComputedRef<boolean>;
}

export const abFieldInjectionKey: InjectionKey<AbFieldContext> =
  Symbol('ab-field');
</script>

<script lang="ts" setup>
// 表单字段容器（取代 ab-label）：label + description + error + aria 接线。
// 控件放默认插槽；ab-input 等会自动消费注入的 id/aria 上下文。
const props = withDefaults(
  defineProps<{
    label: string | (() => string);
    description?: string;
    error?: string;
    required?: boolean;
  }>(),
  {
    description: '',
    error: '',
    required: false,
  }
);

// Vue 类型将 useId 标为可空（组件实例外）；setup 内恒为 string
const controlId = useId() as string;
const labelId = useId() as string;
const descriptionId = useId() as string;
const errorId = useId() as string;

const labelText = computed(() =>
  typeof props.label === 'function' ? props.label() : props.label
);

const describedBy = computed(() => {
  const ids: string[] = [];
  if (props.description) ids.push(descriptionId);
  if (props.error) ids.push(errorId);
  return ids.length > 0 ? ids.join(' ') : undefined;
});

const invalid = computed(() => Boolean(props.error));

// ab-input 等原生控件在挂载时认领 controlId；naive 组件无法接收 id，
// 走 aria-labelledby（此时渲染 span 而非悬空的 label[for]）
const adopted = ref(false);

provide(abFieldInjectionKey, {
  controlId,
  adopted,
  labelId,
  describedBy,
  invalid,
});
</script>

<template>
  <div class="ab-field" :class="{ 'ab-field--invalid': invalid }">
    <div class="ab-field-main">
      <div class="ab-field-heading">
        <Component
          :is="adopted ? 'label' : 'span'"
          :id="labelId"
          class="ab-field-label"
          :for="adopted ? controlId : undefined"
        >
          {{ labelText }}
          <span v-if="required" class="ab-field-required" aria-hidden="true"
            >*</span
          >
        </Component>
        <p v-if="description" :id="descriptionId" class="ab-field-description">
          {{ description }}
        </p>
      </div>

      <div class="ab-field-control">
        <slot></slot>
      </div>
    </div>

    <p v-if="error" :id="errorId" class="ab-field-error" role="alert">
      {{ error }}
    </p>
  </div>
</template>

<style lang="scss" scoped>
.ab-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 100%;
}

.ab-field-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-height: 32px;

  @include forTablet {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
}

.ab-field-heading {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.ab-field-label {
  font-size: 14px;
  color: var(--color-text);
  transition: color var(--transition-normal);
}

.ab-field-required {
  color: var(--color-danger);
}

.ab-field-description {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  max-width: 46ch;
}

.ab-field-control {
  flex-shrink: 0;

  // 移动端控件占满整行（沿用 ab-label 的行为）
  width: 100%;

  @include forTablet {
    width: auto;
  }

  // 沿用旧 ab-label 的控件尺寸约定：下拉框/输入框在桌面端
  // 有 200px 的宽度下限，避免收缩到只剩箭头
  :deep(.n-select),
  :deep(.n-dynamic-tags),
  :deep(.ab-input) {
    width: 100%;

    @include forTablet {
      width: auto;
      min-width: 200px;
    }
  }

  :deep(.ab-input) {
    @include forTablet {
      width: 200px;
    }
  }
}

.ab-field-error {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-danger);

  @include forTablet {
    text-align: right;
  }
}
</style>
