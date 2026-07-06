import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbModal from '../ab-modal.vue';

// headlessui teleports dialogs into document.body and its leave transition
// never completes under happy-dom — wipe the body between tests.
afterEach(() => {
  document.body.innerHTML = '';
});

// matchMedia is mocked to matches:false in setup.ts → desktop dialog branch
async function mountModal(props = {}, slots = {}) {
  const wrapper = mount(AbModal, {
    props: { show: true, title: 'Delete rule?', ...props },
    slots: { default: '<p>body text</p>', ...slots },
    attachTo: document.body,
  });
  // headlessui mounts dialog content on the next tick (transition setup)
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

describe('ab-modal', () => {
  it('renders title and body when shown', async () => {
    const wrapper = await mountModal();
    expect(document.body.textContent).toContain('Delete rule?');
    expect(document.body.textContent).toContain('body text');
    wrapper.unmount();
  });

  it('renders nothing when show is false', async () => {
    const wrapper = await mountModal({ show: false });
    expect(document.body.textContent).not.toContain('Delete rule?');
    wrapper.unmount();
  });

  it('exposes dialog semantics', async () => {
    const wrapper = await mountModal();
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    wrapper.unmount();
  });

  it('renders the footer slot', async () => {
    const wrapper = await mountModal(
      {},
      { footer: '<button id="ok">OK</button>' }
    );
    expect(document.querySelector('#ok')).not.toBeNull();
    wrapper.unmount();
  });

  it('emits update:show false when the close button is clicked', async () => {
    const wrapper = await mountModal();
    const close = document.querySelector(
      '.ab-modal-close'
    ) as HTMLButtonElement;
    expect(close).not.toBeNull();
    close.click();
    await new Promise((resolve) => setTimeout(resolve));
    expect(wrapper.emitted('update:show')?.at(-1)).toEqual([false]);
    wrapper.unmount();
  });

  it('hides the close button when closable is false', async () => {
    const wrapper = await mountModal({ closable: false });
    expect(document.querySelector('.ab-modal-close')).toBeNull();
    wrapper.unmount();
  });
});
