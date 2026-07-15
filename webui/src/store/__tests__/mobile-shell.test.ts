import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useMobileShellStore } from '../mobile-shell';

describe('useMobileShellStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should open the requested overlay when no overlay is active', () => {
    const store = useMobileShellStore();

    store.openOverlay('more');

    expect(store.activeOverlay).toBe('more');
  });

  it('should replace the active overlay when another overlay opens', () => {
    const store = useMobileShellStore();
    store.openOverlay('more');

    store.openOverlay('notifications');

    expect(store.activeOverlay).toBe('notifications');
  });

  it('should close the active overlay when the matching overlay closes', () => {
    const store = useMobileShellStore();
    store.openOverlay('more');

    store.closeOverlay('more');

    expect(store.activeOverlay).toBeNull();
  });

  it('should preserve the active overlay when a stale overlay closes', () => {
    const store = useMobileShellStore();
    store.openOverlay('notifications');

    store.closeOverlay('more');

    expect(store.activeOverlay).toBe('notifications');
  });
});
