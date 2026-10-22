<script lang="ts" setup>
import type { PluginUiSlot } from '@autobangumi/plugin-ui';
import PluginSlot from '@/components/plugin-slot.vue';
import { refreshPluginUi, slotTitle, usePluginUi } from '@/hooks/usePluginUi';

definePage({
  name: 'Plugin',
});

// 插件经 page 挂载点提供的独立页面；同一插件声明多个时取第一个
const route = useRoute('Plugin');
const { slots, loaded, loadFailed } = usePluginUi();
const { lang } = useMyI18n();
const { isMobile } = useBreakpointQuery();
// 离场淡出时 useRoute() 已是下一个路由：只在本路由激活时取参数，否则保留上一个值
const ui = computed<PluginUiSlot | undefined>((prev) =>
  route.name !== 'Plugin'
    ? prev
    : slots.value.find(
        (s) => s.slot === 'page' && s.plugin_id === route.params.id
      )
);
// 同上：离场时保留上一个 id，标题不在淡出中变化
const pluginId = computed<string>((prev) =>
  route.name !== 'Plugin' ? (prev ?? '') : route.params.id
);
</script>

<template>
  <div class="page-plugin">
    <!-- 手机上 ab-page-title 隐藏，页面自己给标题 -->
    <!-- 与 index.vue 的 pageTitle 一致：插件不存在时用 id 作标题 -->
    <h1 v-if="isMobile && (ui || loaded || loadFailed)" class="page-plugin__title">
      {{ ui ? slotTitle(ui, lang) : pluginId }}
    </h1>
    <PluginSlot v-if="ui" :key="`${ui.plugin_id}:${ui.element}`" :ui="ui" />
    <ab-empty
      v-else-if="loaded"
      :title="$t('plugin.page_missing')"
      :description="$t('plugin.page_missing_hint')"
    />
    <ab-empty v-else-if="loadFailed" :title="$t('plugin.load_failed_page')">
      <template #action>
        <ab-button size="sm" @click="refreshPluginUi">
          {{ $t('plugin.retry') }}
        </ab-button>
      </template>
    </ab-empty>
    <ab-skeleton v-else preset="lines" />
  </div>
</template>

<style lang="scss" scoped>
.page-plugin {
  flex-grow: 1;
  min-height: 0;
  overflow: auto;
}

.page-plugin__title {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 650;
}
</style>
