<script setup lang="ts">
import { computed } from 'vue';
import {
  NConfigProvider,
  NDialogProvider,
  NMessageProvider,
  darkTheme,
} from 'naive-ui';
import { abNaiveTheme } from './style/naive-theme';

const { isDark } = useDarkMode();
const { refresh, isLoggedIn } = useAuth();

if (isLoggedIn.value) {
  refresh();
}

const themeOverrides = computed(() =>
  isDark.value ? abNaiveTheme.dark : abNaiveTheme.light
);
const naiveTheme = computed(() => (isDark.value ? darkTheme : null));
</script>

<template>
  <Suspense>
    <NConfigProvider :theme="naiveTheme" :theme-overrides="themeOverrides">
      <NMessageProvider>
        <NDialogProvider>
          <RouterView />
          <ab-confirm-host />
        </NDialogProvider>
      </NMessageProvider>
    </NConfigProvider>
  </Suspense>
</template>

<style lang="scss">
@use './style/var';
@use './style/transition';
@use './style/global';
</style>
