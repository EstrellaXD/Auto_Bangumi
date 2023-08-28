<script lang="ts" setup>

withDefaults(
    defineProps<{
      select: boolean;
      name: string;
      url: string;
      enable: boolean;
      aggregate: boolean;
      parser: string;
    }>(),
    {
      select: false,
      enable: false,
    }
);
</script>

<template>
  <div class="rss-group">
    <div class="left-side" flex space-x-40px>
      <ab-checkbox
          small
          :model-value="select"
          @update:model-value="select = $event"
      />
      <div w-200px text-h3 truncate>{{ name }}</div>
      <div w-300px text-h3 truncate>{{ url }}</div>
    </div>
    <div class="right-side" space-x-8px>
      <ab-tag
          v-if="parser"
          type="primary"
          :title="parser"
      />
      <ab-tag
          v-if="aggregate"
          type="primary"
          title="aggregate"
      />
      <ab-tag
          v-if="enable"
          type="active"
          title="active"
      />
      <ab-tag
          v-if="!enable"
          type="inactive"
          title="inactive"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.rss-group {
  display: flex;
  justify-content: space-between;
  flex-direction: row;
  align-items: center;
  gap: 4px;
}
</style>