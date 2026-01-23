<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    round?: boolean;
    type?: 'large' | 'medium' | 'small';
  }>(),
  {
    round: false,
    type: 'large',
  }
);

defineEmits(['click']);

const buttonSize = computed(() => {
  switch (props.type) {
    case 'large':
      return 'add-btn--large';
    case 'medium':
      return 'add-btn--medium';
    case 'small':
      return 'add-btn--small';
  }
});
</script>

<template>
  <button
    class="add-btn"
    :class="[buttonSize, round && 'add-btn--round']"
    aria-label="Add"
    @click="$emit('click')"
  >
    <svg viewBox="0 0 24 24" fill="none" class="add-btn-icon">
      <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
  </button>
</template>

<style lang="scss" scoped>
.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: #fff;
  border: none;
  cursor: pointer;
  transition: background-color var(--transition-fast),
              transform var(--transition-fast);

  &:hover {
    background: var(--color-primary-hover);
  }

  &:active {
    transform: scale(0.92);
  }

  &--round {
    border-radius: 50%;
  }

  &--large {
    width: 36px;
    height: 36px;
    border-radius: var(--radius-md);

    .add-btn-icon {
      width: 18px;
      height: 18px;
    }
  }

  &--medium {
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);

    .add-btn-icon {
      width: 14px;
      height: 14px;
    }
  }

  &--small {
    width: 20px;
    height: 20px;
    border-radius: 4px;

    .add-btn-icon {
      width: 10px;
      height: 10px;
    }
  }

  &--round.add-btn--large {
    border-radius: 50%;
  }

  &--round.add-btn--medium {
    border-radius: 50%;
  }

  &--round.add-btn--small {
    border-radius: 50%;
  }
}
</style>
