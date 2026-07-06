import { createDiscreteApi } from 'naive-ui';
import type { GlobalThemeOverrides } from 'naive-ui';
import { createSharedComposable } from '@vueuse/core';

// Soft Ink toast：反色墨条 —— 所有类型同一深底，语义色只出现在图标上。
// （组件级 token 可以用 CSS 变量；只有 common 必须是字面量）
const toastTheme: GlobalThemeOverrides = {
  Message: {
    color: 'var(--color-text)',
    colorInfo: 'var(--color-text)',
    colorSuccess: 'var(--color-text)',
    colorError: 'var(--color-text)',
    colorWarning: 'var(--color-text)',
    colorLoading: 'var(--color-text)',
    textColor: 'var(--color-bg)',
    textColorInfo: 'var(--color-bg)',
    textColorSuccess: 'var(--color-bg)',
    textColorError: 'var(--color-bg)',
    textColorWarning: 'var(--color-bg)',
    textColorLoading: 'var(--color-bg)',
    iconColorInfo: 'var(--color-primary-light)',
    iconColorSuccess: 'var(--color-success)',
    iconColorError: 'var(--color-danger)',
    iconColorWarning: 'var(--color-warning)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-md)',
  },
};

export const useMessage = createSharedComposable(() => {
  const { message } = createDiscreteApi(['message'], {
    configProviderProps: { themeOverrides: toastTheme },
  });
  return message;
});
