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
    <div bg-white rounded-12px px-8px text-10px :class="InnerStyle">
      {{ title }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
// border
$primary: linear-gradient(90.5deg, #492897 1.53%, #783674 96.48%);
$warn: #892F2F;
$inactive: #797979;
$active: #104931;
$notify: #F5C451;

//inner
$primary-inner: #EEE5F4;
$warn-inner: #FFDFDF;
$inactive-inner: #E0E0E0;
$active-inner: #E5F4E0;
$notify-inner: #FFF4DB;

//font-color
$primary-font: #000000;
$warn-font: #892F2F;
$inactive-font: #3F3F3F;
$active-font: #4C6643;
$notify-font: #A76E18;

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
