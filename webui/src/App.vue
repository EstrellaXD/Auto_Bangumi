<script setup lang="ts">
import { computed } from 'vue';
import { type GlobalThemeOverrides, NConfigProvider, NMessageProvider, darkTheme } from 'naive-ui';

const { isDark } = useDarkMode();
const { refresh, isLoggedIn } = useAuth();

if (isLoggedIn.value) {
  refresh();
}

const lightOverrides: GlobalThemeOverrides = {
  common: {
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
  common: {
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

const themeOverrides = computed(() => isDark.value ? darkOverrides : lightOverrides);
const naiveTheme = computed(() => isDark.value ? darkTheme : null);
</script>

<template>
  <Suspense>
    <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
      <NMessageProvider>
        <RouterView></RouterView>
      </NMessageProvider>
    </NConfigProvider>
  </Suspense>
</template>

<style lang="scss">
@import './style/var';
@import './style/transition';
@import './style/global';
</style>
