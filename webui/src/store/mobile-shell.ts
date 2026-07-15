export type MobileOverlay = 'more' | 'notifications' | 'action';

export const useMobileShellStore = defineStore('mobile-shell', () => {
  const activeOverlay = ref<MobileOverlay | null>(null);

  function openOverlay(overlay: MobileOverlay) {
    activeOverlay.value = overlay;
  }

  function closeOverlay(overlay?: MobileOverlay) {
    if (overlay && activeOverlay.value !== overlay) return;
    activeOverlay.value = null;
  }

  return {
    activeOverlay,
    openOverlay,
    closeOverlay,
  };
});
