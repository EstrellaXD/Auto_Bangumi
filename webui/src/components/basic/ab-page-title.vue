<script lang="ts" setup>
withDefaults(
  defineProps<{
    title: string;
  }>(),
  {
    title: 'title',
  }
);
</script>

<template>
  <div class="page-title">
    <h1 class="page-title-text">{{ title }}</h1>
    <div class="page-title-accent"></div>
  </div>
</template>

<style lang="scss" scoped>
.page-title {
  display: none;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;

  @include forTablet {
    display: flex;
  }
}

.page-title-text {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  transition: color var(--transition-normal);

  @include forMobile {
    font-size: 18px;
  }
}

.page-title-accent {
  width: 120px;
  height: 3px;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-hover));
  opacity: 0.6;

  @include forMobile {
    width: 80px;
  }
}
</style>
