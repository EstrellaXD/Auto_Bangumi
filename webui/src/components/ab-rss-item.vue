<script lang="ts" setup>
import { ref } from 'vue';

withDefaults(
  defineProps<{
    id: number;
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

defineEmits<{
  (e: 'on-select', checked: boolean, id: number): void;
}>();

const checked = ref(false);
</script>

<template>
  <div flex="~ items-center justify-between gap-4">
    <!-- left -->
    <div flex="~ gap-x-40">
      <ab-checkbox
        v-model="checked"
        small
        @click="() => $emit('on-select', checked, id)"
      />
      <div w-200 text-h3 truncate>{{ name }}</div>
      <div w-300 text-h3 truncate>{{ url }}</div>
    </div>

    <!-- right -->
    <div space-x-8>
      <ab-tag v-if="parser" type="primary" :title="parser" />
      <ab-tag v-if="aggregate" type="primary" title="aggregate" />
      <ab-tag v-if="enable" type="active" title="active" />
      <ab-tag v-if="!enable" type="inactive" title="inactive" />
    </div>
  </div>
</template>
