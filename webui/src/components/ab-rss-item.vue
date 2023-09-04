<script lang="ts" setup>
import { ref } from 'vue';

withDefaults(
    defineProps<{
      name: string;
      url: string;
      enable: boolean;
      aggregate: boolean;
      parser: string;
    }>(),
    {
      aggregate: false,
    }
);

defineEmits(['on-select']);

const checked = ref(false);
</script>

<template>
  <div class="rss-group">
    <div class="left-side" flex space-x-40px>
      <ab-checkbox
          small
          :model-value="checked"
          @update:model-value="checked = $event"
          @click="() => $emit('on-select')"
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