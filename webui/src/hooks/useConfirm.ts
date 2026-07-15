import { reactive } from 'vue';

export interface ConfirmOptions {
  title: string;
  body?: string;
  confirmText?: string;
  cancelText?: string;
  /** 破坏性操作：确认按钮使用 danger 变体 */
  danger?: boolean;
}

export interface ConfirmFocusOptions {
  /** 对话框取消后恢复焦点的持久元素。 */
  returnFocus?: HTMLElement | null;
}

interface ConfirmRequest extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

// 模块级单例状态：ab-confirm-host（挂载于 App.vue）消费并渲染
const state = reactive<{ current: ConfirmRequest | null }>({ current: null });
let returnFocusCycleActive = false;
let cycleReturnFocus: HTMLElement | null = null;
let restoreAfterLeave = false;
let focusCycleGeneration = 0;

function captureReturnFocus(
  explicitTarget?: HTMLElement | null
): HTMLElement | null {
  if (typeof document === 'undefined' || typeof HTMLElement === 'undefined') {
    return null;
  }

  const target = explicitTarget ?? document.activeElement;
  return target instanceof HTMLElement &&
    target !== document.body &&
    target !== document.documentElement &&
    target.isConnected
    ? target
    : null;
}

/**
 * Promise 式确认对话框，替代 NPopconfirm / 手搭确认弹窗：
 * `if (await confirm({ title, danger: true })) { … }`
 */
export function useConfirm() {
  function confirm(
    options: ConfirmOptions,
    focusOptions: ConfirmFocusOptions = {}
  ): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      // Replacements and dialogs reopened during a leave transition belong to
      // one focus cycle. Keep the first durable trigger for that whole cycle.
      if (!returnFocusCycleActive) {
        cycleReturnFocus = captureReturnFocus(focusOptions.returnFocus);
        returnFocusCycleActive = true;
        focusCycleGeneration += 1;
      }
      // 已有未决确认时，先取消旧的，避免悬挂的 Promise
      state.current?.resolve(false);
      restoreAfterLeave = false;
      state.current = { ...options, resolve };
    });
  }

  return { confirm };
}

/** 仅供 ab-confirm-host 内部使用 */
export function useConfirmState() {
  function settle(value: boolean) {
    const request = state.current;
    if (!request) return;

    restoreAfterLeave = !value;
    request.resolve(value);
    state.current = null;
  }

  function restoreFocus() {
    // A replacement may have reopened before an earlier leave callback fires.
    if (state.current) return;

    const target = cycleReturnFocus;
    const shouldRestore = restoreAfterLeave;
    const generation = focusCycleGeneration;
    cycleReturnFocus = null;
    restoreAfterLeave = false;
    returnFocusCycleActive = false;
    if (!shouldRestore || !target?.isConnected) return;

    // Headless UI may remove its focus trap after TransitionRoot emits
    // after-leave. Restore in the next microtask so that teardown cannot
    // override the persistent trigger, while rejecting stale focus cycles.
    queueMicrotask(() => {
      if (
        focusCycleGeneration !== generation ||
        returnFocusCycleActive ||
        state.current ||
        !target.isConnected
      ) {
        return;
      }
      target.focus();
    });
  }

  return { state, settle, restoreFocus };
}
