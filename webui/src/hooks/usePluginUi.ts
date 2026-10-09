import type { PluginUiSlot, UiSlot } from '@autobangumi/plugin-ui';
import { apiPlugins } from '@/api/plugins';

const slots = ref<PluginUiSlot[]>([]);
const loaded = ref(false);
const loadFailed = ref(false);
let requested = false;

/** 重新拉取已启用插件的前端挂载点；插件启停后调用。 */
export async function refreshPluginUi() {
  requested = true;
  loadFailed.value = false;
  try {
    slots.value = await apiPlugins.ui();
    loaded.value = true;
  } catch {
    // 未登录或请求失败：保持现状，下次使用时重试
    requested = false;
    loadFailed.value = true;
  }
}

/**
 * 挂载点列表，首次使用时请求；`loaded` 为 true 之后列表才算可信。
 * `loadFailed` 为 true 表示请求失败，页面可据此提供重试。
 */
export function usePluginUi() {
  if (!requested) refreshPluginUi();
  return { slots, loaded, loadFailed };
}

/** 某个挂载点上的全部插件组件。 */
export function useUiSlots(slot: UiSlot) {
  const { slots: all } = usePluginUi();
  return computed(() => all.value.filter((s) => s.slot === slot));
}

/** 按当前语言取标题：`zh-CN` → `en-US` → 第一个。 */
export function slotTitle(ui: PluginUiSlot, locale: string): string {
  return ui.title[locale] ?? ui.title['en-US'] ?? Object.values(ui.title)[0];
}
