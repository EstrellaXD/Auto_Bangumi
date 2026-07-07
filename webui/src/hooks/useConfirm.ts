import { reactive } from 'vue';

export interface ConfirmOptions {
  title: string;
  body?: string;
  confirmText?: string;
  cancelText?: string;
  /** 破坏性操作：确认按钮使用 danger 变体 */
  danger?: boolean;
}

interface ConfirmRequest extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

// 模块级单例状态：ab-confirm-host（挂载于 App.vue）消费并渲染
const state = reactive<{ current: ConfirmRequest | null }>({ current: null });

/**
 * Promise 式确认对话框，替代 NPopconfirm / 手搭确认弹窗：
 * `if (await confirm({ title, danger: true })) { … }`
 */
export function useConfirm() {
  function confirm(options: ConfirmOptions): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      // 已有未决确认时，先取消旧的，避免悬挂的 Promise
      state.current?.resolve(false);
      state.current = { ...options, resolve };
    });
  }

  return { confirm };
}

/** 仅供 ab-confirm-host 内部使用 */
export function useConfirmState() {
  function settle(value: boolean) {
    state.current?.resolve(value);
    state.current = null;
  }

  return { state, settle };
}
