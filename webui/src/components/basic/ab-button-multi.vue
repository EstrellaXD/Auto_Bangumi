<script lang="ts" setup>
import { NSpin } from 'naive-ui';
import { Down } from '@icon-park/vue-next';

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'warn';
    size?: 'big' | 'normal' | 'small';
    link?: string | null;
    loading?: boolean;
    selections: string[];
  }>(),
  {
    type: 'primary',
    size: 'normal',
    link: null,
    loading: false,
  }
);

defineEmits(['click']);

const selected = ref<string>(props.selections[0]);
const showSelections = ref<boolean>(false);
</script>

<template>
  <div class="btn-multi" :class="[`btn-multi--${size}`, `btn-multi--${type}`]">
    <Component
      :is="link !== null ? 'a' : 'button'"
      :href="link"
      class="btn-multi-main"
      @click="$emit('click', selected)"
    >
      <NSpin :show="loading" :size="size === 'big' ? 'large' : 'small'">
        <div class="btn-multi-label">{{ selected }}</div>
      </NSpin>
    </Component>
    <div
      class="btn-multi-arrow"
      @click="() => (showSelections = !showSelections)"
    >
      <Down fill="white" />
    </div>
  </div>

  <div
    v-if="showSelections"
    class="btn-multi-dropdown"
    :class="[`btn-multi--${size}`, `btn-multi--${type}`]"
  >
    <div
      v-for="selection in selections"
      :key="selection"
      class="btn-multi-option"
      @click="() => { selected = selection; showSelections = false; }"
    >
      {{ selection }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
.btn-multi {
  display: flex;
  align-items: center;
  overflow: hidden;
  color: #fff;

  &--big {
    border-radius: var(--radius-md);
    width: 276px;
    height: 55px;
    font-size: 24px;
  }

  &--normal {
    border-radius: var(--radius-sm);
    width: 170px;
    height: 36px;
    font-size: 14px;
  }

  &--small {
    border-radius: var(--radius-sm);
    width: 86px;
    height: 28px;
    font-size: 12px;
  }

  &--primary {
    .btn-multi-main,
    .btn-multi-arrow,
    .btn-multi-option {
      background: var(--color-primary);
    }
    .btn-multi-main:hover,
    .btn-multi-arrow:hover,
    .btn-multi-option:hover {
      background: var(--color-primary-hover);
    }
  }

  &--warn {
    .btn-multi-main,
    .btn-multi-arrow,
    .btn-multi-option {
      background: var(--color-danger);
    }
    .btn-multi-main:hover,
    .btn-multi-arrow:hover,
    .btn-multi-option:hover {
      filter: brightness(0.9);
    }
  }
}

.btn-multi-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding-left: 12px;
  border: none;
  outline: none;
  color: inherit;
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.btn-multi-label {
  font-size: inherit;
}

.btn-multi-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  height: 100%;
  cursor: pointer;
  user-select: none;
  transition: background-color var(--transition-fast);
}

.btn-multi-dropdown {
  position: absolute;
  z-index: 70;
  overflow: hidden;
  transform: translateY(80%) translateX(-111%);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
}

.btn-multi-option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 8px 0;
  cursor: pointer;
  user-select: none;
  color: #fff;
  font-size: inherit;
  transition: background-color var(--transition-fast);
}
</style>
