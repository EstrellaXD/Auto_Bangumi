<script lang="ts" setup>

withDefaults(
    defineProps<{
      type: 'primary' | 'warn' | 'inactive' | 'active' | 'notify';
      title: string;
    }>(),
    {
      type: 'primary',
      title: 'title',
    }
);


</script>

<template>
  <div class="round-label" :class="type">
    {{ title }}
  </div>
</template>

<style lang="scss" scoped>
// border
$primary: #4e3c94;
$warn: #892F2F;
$inactive: #797979;
$active: #104931;
$notify: #F5C451;

//inner
$primary-inner: #EEE5F4;
$warn-inner: #FFDFDF;
$inactive-inner: #E0E0E0;
$active-inner:#E5F4E0;
$notify-inner: #FFF4DB;

//font-color
$primary-font: #000000;
$warn-font: #892F2F;
$inactive-font: #3F3F3F;
$active-font: #4C6643;
$notify-font: #A76E18;


.round-label {
    padding: 2px 12px;
    font-size: 10px;
    display: inline-flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    border-radius: 12px;
}

.primary {
    border: 1px solid $primary;
    background-color: $primary-inner;
    color: $primary-font;
}

.warn {
    border: 1px solid $warn;
    background-color: $warn-inner;
    color: $warn-font;
}

.inactive {
    border: 1px solid $inactive;
    background-color: $inactive-inner;
    color: $inactive-font;
}

.active {
    border: 1px solid $active;
    background-color: $active-inner;
    color: $active-font;
}

.notify {
    border: 1px solid $notify;
    background-color: $notify-inner;
    color: $notify-font;
}

</style>
