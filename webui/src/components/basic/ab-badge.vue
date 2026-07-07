<script lang="ts" setup>
// 计数/圆点徽标（通知中心等）：溢出显示 max+，count 为 0 时隐藏。
const props = withDefaults(
  defineProps<{
    count?: number;
    /** 只显示小圆点（不显示数字） */
    dot?: boolean;
    max?: number;
  }>(),
  {
    count: 0,
    dot: false,
    max: 99,
  }
);

const visible = computed(() => props.dot || props.count > 0);
const text = computed(() =>
  props.count > props.max ? `${props.max}+` : String(props.count)
);
</script>

<template>
  <span
    v-if="visible"
    class="ab-badge"
    :class="{ 'ab-badge--dot': dot }"
    aria-hidden="true"
  >
    <template v-if="!dot">{{ text }}</template>
  </span>
</template>

<style lang="scss" scoped>
.ab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--color-danger);
  color: var(--color-white);
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;

  &--dot {
    min-width: 8px;
    width: 8px;
    height: 8px;
    padding: 0;
  }
}
</style>
