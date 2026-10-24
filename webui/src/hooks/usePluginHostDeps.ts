import tokensCss from '@autobangumi/plugin-ui/tokens.css?inline';
import type { HostDeps } from '@/services/plugin-host';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useEventStream } from '@/hooks/useEventStream';
import { useMessage } from '@/hooks/useMessage';
import { useMyI18n } from '@/hooks/useMyI18n';
import { axios } from '@/utils/axios';

/** 注入 Shadow DOM 的主题变量定义（`--ab-*`） */
export { tokensCss };

const TOKEN_NAMES = [...tokensCss.matchAll(/(--ab-[a-z0-9-]+)\s*:/g)].map(
  (match) => match[1]
);

/**
 * 插件组件的宿主能力（语言、深浅色、toast、事件、带登录态的请求）。
 * 在组件 setup 中调用，返回的函数按挂载容器生成一份 HostDeps。
 */
export function usePluginHostDeps() {
  const { lang, i18n } = useMyI18n();
  const { isDark } = useDarkMode();
  const message = useMessage();
  const { onBus } = useEventStream();

  return (container: HTMLElement): HostDeps => ({
    // 请求出错由插件自己处理，宿主不再弹统一的错误提示
    request: async (method, url, { params, data }) => {
      const res = await axios.request({
        method,
        url,
        params,
        data,
        silent: true,
      });
      return res.data;
    },
    locale: () => (lang.value === 'zh-CN' ? 'zh-CN' : 'en-US'),
    t: (key, params) =>
      i18n.global.te(key) ? i18n.global.t(key, params ?? {}) : key,
    isDark: () => isDark.value,
    tokens: () => {
      const style = getComputedStyle(container);
      return Object.fromEntries(
        TOKEN_NAMES.map((name) => [name, style.getPropertyValue(name).trim()])
      );
    },
    toast: (text, kind) =>
      kind === 'error' ? message.error(text) : message.info(text),
    onBusEvent: onBus,
  });
}
