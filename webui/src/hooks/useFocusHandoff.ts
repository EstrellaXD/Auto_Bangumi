/**
 * Keep a focus target outside a sequence of dialogs, then restore it before
 * the next dialog mounts so that dialog captures a durable return target.
 */
export function useFocusHandoff() {
  let target: HTMLElement | null = null;

  function captureFocusTarget(candidate?: Element | null): void {
    if (typeof document === 'undefined' || typeof HTMLElement === 'undefined') {
      target = null;
      return;
    }

    const nextTarget = candidate ?? document.activeElement;
    target =
      nextTarget instanceof HTMLElement &&
      nextTarget !== document.body &&
      nextTarget !== document.documentElement &&
      nextTarget.isConnected
        ? nextTarget
        : null;
  }

  function restoreFocusTarget(): void {
    if (!target?.isConnected) {
      target = null;
      return;
    }
    target.focus();
  }

  return { captureFocusTarget, restoreFocusTarget };
}
