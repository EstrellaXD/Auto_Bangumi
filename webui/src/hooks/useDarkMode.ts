import { computed, ref, watch } from 'vue';
import { createSharedComposable, usePreferredDark } from '@vueuse/core';

type ThemeMode = 'light' | 'dark' | 'system';

export const useDarkMode = createSharedComposable(() => {
  const prefersDark = usePreferredDark();
  const stored = localStorage.getItem('theme') as ThemeMode | null;
  const mode = ref<ThemeMode>(stored || 'system');

  const isDark = computed(() => {
    if (mode.value === 'system') return prefersDark.value;
    return mode.value === 'dark';
  });

  function applyTheme() {
    const html = document.documentElement;
    if (isDark.value) {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  }

  function setMode(newMode: ThemeMode) {
    mode.value = newMode;
    if (newMode === 'system') {
      localStorage.removeItem('theme');
    } else {
      localStorage.setItem('theme', newMode);
    }
  }

  function toggle() {
    setMode(isDark.value ? 'light' : 'dark');
  }

  watch(isDark, applyTheme, { immediate: true });
  watch(prefersDark, () => {
    if (mode.value === 'system') applyTheme();
  });

  return {
    mode,
    isDark,
    setMode,
    toggle,
  };
});
