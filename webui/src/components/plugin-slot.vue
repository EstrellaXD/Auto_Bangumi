<script lang="ts" setup>
import type { AbPluginElement, PluginUiSlot } from '@autobangumi/plugin-ui';
import { tokensCss, usePluginHostDeps } from '@/hooks/usePluginHostDeps';
import { loadPluginElement, watchPluginErrors } from '@/services/plugin-loader';
import { createAbHost } from '@/services/plugin-host';

// 前端挂载点（设计文档 3.8）：导入插件模块，在 Shadow DOM 中创建它声明的
// custom element，并把 host / context 设置好后再插入文档。加载失败、元素
// 未定义或运行时抛错时，只有这个挂载点显示失败提示，页面其余部分不受影响。
const props = defineProps<{
  ui: PluginUiSlot;
  context?: Record<string, unknown>;
}>();

const container = ref<HTMLElement>();
const failed = ref(false);
const loading = ref(true);
const reason = ref('');
const hostDeps = usePluginHostDeps();

let generation = 0;
let teardown: (() => void) | null = null;

function fail(error: unknown) {
  // 不用 `[plugin:id]` 式模板串：UnoCSS 的 attributify 会把它当成样式规则
  console.error('plugin component failed:', props.ui.plugin_id, error);
  failed.value = true;
  loading.value = false;
  reason.value = error instanceof Error ? error.message : String(error ?? '');
  teardown?.();
  teardown = null;
}

async function mount() {
  const target = container.value;
  if (!target) return;
  const current = ++generation;
  failed.value = false;
  loading.value = true;
  try {
    await loadPluginElement(props.ui);
    // 等待导入期间已卸载或上下文又变了：丢弃这一次
    if (current !== generation) return;

    const { host, dispose } = createAbHost(
      props.ui.plugin_id,
      hostDeps(target)
    );
    const element = document.createElement(props.ui.element) as AbPluginElement;
    element.host = host;
    element.context = { ...props.context } as never;

    // 包裹用的 Shadow DOM：隔离宿主的全局样式，并提供 --ab-* 主题变量
    const root = target.shadowRoot ?? target.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = tokensCss;
    root.replaceChildren(style);

    const stopWatching = watchPluginErrors(props.ui.plugin_id, fail);
    teardown = () => {
      stopWatching();
      dispose();
      root.replaceChildren();
    };
    root.append(element);
    loading.value = false;
  } catch (error) {
    fail(error);
  }
}

// 浏览器会缓存求值失败的模块（插件加载器只丢弃失败的 Promise），
// 原地重新导入无法恢复，只能刷新页面
function reload() {
  location.reload();
}

function unmount() {
  generation += 1;
  teardown?.();
  teardown = null;
}

onMounted(mount);
onBeforeUnmount(unmount);
// 上下文（如番剧 id）变化时重建元素，组件无需自己监听
watch(
  () => JSON.stringify(props.context ?? {}),
  () => {
    unmount();
    mount();
  }
);
</script>

<template>
  <div class="plugin-slot" :aria-busy="loading">
    <ab-skeleton v-if="loading" preset="lines" :count="2" />
    <ab-alert v-if="failed" type="danger" :title="$t('plugin.load_failed')">
      <span class="plugin-slot__id">{{ ui.plugin_id }}</span>
      <span v-if="reason" class="plugin-slot__id">{{ reason }}</span>
      {{ $t('plugin.load_failed_hint') }}
      <template #action>
        <ab-button size="sm" @click="reload">{{
          $t('plugin.reload')
        }}</ab-button>
      </template>
    </ab-alert>
    <div v-show="!failed" ref="container" class="plugin-slot__body"></div>
  </div>
</template>

<style lang="scss" scoped>
.plugin-slot {
  min-width: 0;
}

.plugin-slot__id {
  font-family: var(--font-mono);
}
</style>
