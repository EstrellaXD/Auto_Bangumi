import { afterEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import AbBottomSheet from '../ab-bottom-sheet.vue';

afterEach(() => {
  document.body.innerHTML = '';
  vi.restoreAllMocks();
});

function installVisualViewport() {
  const viewport = {
    height: 500,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  Object.defineProperty(window, 'visualViewport', {
    configurable: true,
    value: viewport,
  });
  return viewport;
}

async function mountSheet(props = {}) {
  const wrapper = mount(AbBottomSheet, {
    props: { show: true, title: 'Edit rule', ...props },
    slots: { default: '<input id="title-input" />' },
    attachTo: document.body,
  });
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

describe('ab-bottom-sheet', () => {
  it('should expose its title as the dialog accessible name', async () => {
    await mountSheet();

    const dialog = document.querySelector('[role="dialog"]');
    const labelledBy = dialog?.getAttribute('aria-labelledby');
    expect(labelledBy).toBeTruthy();
    expect(document.getElementById(labelledBy!)?.textContent).toContain(
      'Edit rule'
    );
  });

  it('should provide an accessible close action', async () => {
    const wrapper = await mountSheet({ closeLabel: 'Dismiss sheet' });

    const closeButton = document.querySelector<HTMLButtonElement>(
      'button[aria-label="Dismiss sheet"]'
    );
    expect(closeButton).not.toBeNull();
    expect(closeButton!.classList.contains('ab-icon-btn--md')).toBe(true);
    closeButton!.click();
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('update:show')).toEqual([[false]]);
    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  it('should hide the close action when requested', async () => {
    await mountSheet({ showClose: false });

    expect(document.querySelector('button[aria-label="Close"]')).toBeNull();
  });

  it('should render the fullscreen panel class when requested', async () => {
    await mountSheet({ fullscreen: true, avoidKeyboard: false });

    const panel = document.querySelector('[data-testid="bottom-sheet-panel"]');
    expect(panel).not.toBeNull();
    expect(
      panel?.classList.contains('ab-bottom-sheet__panel--fullscreen')
    ).toBe(true);
  });

  it('should not translate the sheet for keyboard changes when avoidance is disabled', async () => {
    const viewport = installVisualViewport();

    await mountSheet({ avoidKeyboard: false });

    expect(viewport.addEventListener).not.toHaveBeenCalled();
  });
});
