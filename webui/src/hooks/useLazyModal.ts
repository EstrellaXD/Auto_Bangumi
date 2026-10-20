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
        try {
          comp.value = (await load()).default;
        } catch {
          // 升级后旧的分包 404：整页刷新一次拿新入口，sessionStorage 标记防止循环刷新
          try {
            if (!sessionStorage.getItem('lazy-modal-reload')) {
              sessionStorage.setItem('lazy-modal-reload', '1');
              location.reload();
            }
          } catch {
            // sessionStorage 不可用时不刷新，避免无限循环
          }
          return;
        }
        await nextTick();
      }
      shown.value = open.value;
    },
    { immediate: true }
  );

  return { comp, shown };
}
