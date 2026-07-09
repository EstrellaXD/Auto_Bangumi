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
  it('should render the fullscreen panel class when requested', async () => {
    await mountSheet({ fullscreen: true, avoidKeyboard: false });

    expect(
      document.querySelector('.ab-bottom-sheet__panel--fullscreen')
    ).not.toBeNull();
  });

  it('should not translate the sheet for keyboard changes when avoidance is disabled', async () => {
    const viewport = installVisualViewport();

    await mountSheet({ avoidKeyboard: false });

    expect(viewport.addEventListener).not.toHaveBeenCalled();
  });
});
