<script lang="ts" setup>
import PluginSlot from '@/components/plugin-slot.vue';
import { usePluginUi } from '@/hooks/usePluginUi';

definePage({
  name: 'Plugin',
});

// 插件经 page 挂载点提供的独立页面；同一插件声明多个时取第一个
const route = useRoute();
const { slots, loaded } = usePluginUi();
const ui = computed(() =>
  slots.value.find(
    (s) =>
      s.slot === 'page' &&
      s.plugin_id === (route.params as Record<string, string>).id
  )
);
</script>

<template>
  <div class="page-plugin">
    <PluginSlot v-if="ui" :key="`${ui.plugin_id}:${ui.element}`" :ui="ui" />
    <ab-empty
      v-else-if="loaded"
      :title="$t('plugin.page_missing')"
      :description="$t('plugin.page_missing_hint')"
    />
  </div>
</template>

<style lang="scss" scoped>
.page-plugin {
  flex-grow: 1;
  min-height: 0;
  overflow: auto;
}
</style>
