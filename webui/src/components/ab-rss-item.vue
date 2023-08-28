<script lang="ts" setup>

withDefaults(
    defineProps<{
      name: string;
      url: string;
      enable: boolean;
      aggregate: boolean;
      parser: string;
    }>(),
    {
      enable: false,
    }
);
</script>

<template>
    <div flex>
      <ab-checkbox
          small
          :model-value="enable"
      />
      <div text-h3 truncate>{{ name }}</div>
      <div w-300px text-h3 truncate>{{ url }}</div>
      <div>{{ parser }}</div>
    </div>
</template>