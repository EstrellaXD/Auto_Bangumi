<script setup lang="ts">
import { computed } from 'vue';
import {
  type GlobalThemeOverrides,
  NConfigProvider,
  NDialogProvider,
  NMessageProvider,
  darkTheme,
} from 'naive-ui';

const { isDark } = useDarkMode();
const { refresh, isLoggedIn } = useAuth();

if (isLoggedIn.value) {
  refresh();
}

// Button/Select/Switch tokens reference the app's own CSS custom properties
// directly (they resolve correctly under both `:root` and `.dark`), so they
// don't need to be duplicated between the light/dark override objects below.
// 注意：common 里的颜色 token 会进入 naive-ui (seemly) 的 JS 颜色计算，
// 写 CSS 变量会抛 "[seemly/rgba]: Invalid color value var(...)" 并让整个
// 页面渲染崩溃（Config 页曾因此白屏）——必须用字面量，按主题各写一份。
const primitiveOverrides: GlobalThemeOverrides = {
  Button: {
    borderRadiusTiny: 'var(--radius-sm)',
    borderRadiusSmall: 'var(--radius-sm)',
    borderRadiusMedium: 'var(--radius-sm)',
    borderRadiusLarge: 'var(--radius-md)',
  },
  Switch: {
    railColorActive: 'var(--color-primary)',
  },
  // Soft Ink：输入类控件为填充式（surface-2），无边框；
  // 边框与描边只在聚焦时出现（primary）
  Input: {
    color: 'var(--color-surface-2)',
    colorFocus: 'var(--color-surface)',
    border: '1px solid transparent',
    borderHover: '1px solid transparent',
    borderFocus: '1px solid var(--color-primary)',
    boxShadowFocus: '0 0 0 2px var(--color-primary-alpha)',
    borderRadius: 'var(--radius-sm)',
  },
  Select: {
    peers: {
      InternalSelection: {
        color: 'var(--color-surface-2)',
        colorActive: 'var(--color-surface)',
        border: '1px solid transparent',
        borderHover: '1px solid transparent',
        borderFocus: '1px solid var(--color-primary)',
        borderActive: '1px solid var(--color-primary)',
        boxShadowFocus: '0 0 0 2px var(--color-primary-alpha)',
        boxShadowActive: '0 0 0 2px var(--color-primary-alpha)',
        borderRadius: 'var(--radius-sm)',
      },
    },
  },
  Popover: {
    borderRadius: 'var(--radius-md)',
  },
  Dialog: {
    borderRadius: 'var(--radius-md)',
  },
};

const lightOverrides: GlobalThemeOverrides = {
  ...primitiveOverrides,
  common: {
    errorColor: '#EF4444',
    errorColorHover: '#DC2626',
    errorColorPressed: '#B91C1C',
    errorColorSuppl: '#EF4444',
    primaryColor: '#6C4AB6',
    primaryColorHover: '#563A92',
    primaryColorPressed: '#4A3291',
    bodyColor: '#FAFAFA',
    cardColor: '#FFFFFF',
    borderColor: '#E2E8F0',
    textColorBase: '#1E293B',
    textColor1: '#1E293B',
    textColor2: '#64748B',
    textColor3: '#94A3B8',
  },
  Spin: {
    color: '#6C4AB6',
  },
  DataTable: {
    thColor: 'transparent',
    thColorHover: 'transparent',
    tdColorHover: 'var(--color-surface-hover)',
    borderColor: 'var(--color-border)',
  },
  Checkbox: {
    colorChecked: '#6C4AB6',
    borderFocus: '#6C4AB6',
    boxShadowFocus: '0 0 0 2px rgba(108, 74, 182, 0.2)',
    borderChecked: '1px solid #6C4AB6',
  },
};

const darkOverrides: GlobalThemeOverrides = {
  ...primitiveOverrides,
  common: {
    errorColor: '#F87171',
    errorColorHover: '#EF4444',
    errorColorPressed: '#DC2626',
    errorColorSuppl: '#F87171',
    primaryColor: '#8B6CC7',
    primaryColorHover: '#A78BDB',
    primaryColorPressed: '#7B5CB7',
    bodyColor: '#0F172A',
    cardColor: '#1E293B',
    borderColor: '#334155',
    textColorBase: '#F1F5F9',
    textColor1: '#F1F5F9',
    textColor2: '#94A3B8',
    textColor3: '#64748B',
  },
  Spin: {
    color: '#8B6CC7',
  },
  DataTable: {
    thColor: 'transparent',
    thColorHover: 'transparent',
    tdColorHover: 'var(--color-surface-hover)',
    borderColor: 'var(--color-border)',
  },
  Checkbox: {
    colorChecked: '#8B6CC7',
    borderFocus: '#8B6CC7',
    boxShadowFocus: '0 0 0 2px rgba(139, 108, 199, 0.2)',
    borderChecked: '1px solid #8B6CC7',
  },
};

const themeOverrides = computed(() =>
  isDark.value ? darkOverrides : lightOverrides
);
const naiveTheme = computed(() => (isDark.value ? darkTheme : null));
</script>

<template>
  <Suspense>
    <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
      <NMessageProvider>
        <NDialogProvider>
          <RouterView></RouterView>
          <ab-confirm-host />
        </NDialogProvider>
      </NMessageProvider>
    </NConfigProvider>
  </Suspense>
</template>

<style lang="scss">
@import './style/var';
@import './style/transition';
@import './style/global';
</style>
