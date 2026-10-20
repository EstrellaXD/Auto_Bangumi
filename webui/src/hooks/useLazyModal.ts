import type { Component, Ref } from 'vue';

/**
 * 弹窗首次打开时才加载并挂载。
 * `comp` 就绪后才渲染，`shown` 在挂载后的下一拍再置为 true，
 * 这样 NModal 的进入过渡（appear）仍然生效。
 */
export function useLazyModal(
  open: Ref<boolean>,
  load: () => Promise<{ default: Component }>
) {
  const comp = shallowRef<Component>();
  const shown = ref(false);

  watch(
    open,
    async (val) => {
      if (val && !comp.value) {
        comp.value = (await load()).default;
        await nextTick();
      }
      shown.value = open.value;
    },
    { immediate: true }
  );

  return { comp, shown };
}
