<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    type: 'primary' | 'warn' | 'inactive' | 'active' | 'notify';
    title: string;
  }>(),
  {
    type: 'primary',
    title: 'title',
  }
);

const InnerStyle = computed(() => {
  return `${props.type}-inner`;
});
</script>

<template>
  <div p-1px rounded-16px inline-flex :class="type">
    <div
      bg-white
      rounded-12px
      px-8px
      text-10px
      truncate
      max-w-72px
      :class="InnerStyle"
    >
      {{ title }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
// border
$primary: linear-gradient(90.5deg, #492897 1.53%, #783674 96.48%);
$warn: #892f2f;
$inactive: #797979;
$active: #104931;
$notify: #f5c451;

//inner
$primary-inner: #eee5f4;
$warn-inner: #ffdfdf;
$inactive-inner: #e0e0e0;
$active-inner: #e5f4e0;
$notify-inner: #fff4db;

//font-color
$primary-font: #000000;
$warn-font: #892f2f;
$inactive-font: #3f3f3f;
$active-font: #4c6643;
$notify-font: #a76e18;

.primary {
  background: $primary;
}

.primary-inner {
  background: $primary-inner;
  color: $primary-font;
}

.warn {
  background: $warn;
}

.warn-inner {
  background: $warn-inner;
  color: $warn-font;
}

.inactive {
  background: $inactive;
}

.inactive-inner {
  background: $inactive-inner;
  color: $inactive-font;
}

.active {
  background: $active;
}

.active-inner {
  background: $active-inner;
  color: $active-font;
}

.notify {
  background: $notify;
}

.notify-inner {
  background: $notify-inner;
  color: $notify-font;
}
</style>
