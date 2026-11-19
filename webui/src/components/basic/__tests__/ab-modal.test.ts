import { afterEach, describe, expect, it } from 'vitest';
import { defineComponent, ref } from 'vue';
import { mount } from '@vue/test-utils';
import AbModal from '../ab-modal.vue';

// NModal teleports dialogs into document.body and its leave transition
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
    global: { stubs: { transition: false } },
  });
  // NModal mounts dialog content on the next tick (transition setup)
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

describe('ab-modal', () => {
  it('should render title and body when shown', async () => {
    const wrapper = await mountModal();
    expect(document.body.textContent).toContain('Delete rule?');
    expect(document.body.textContent).toContain('body text');
    wrapper.unmount();
  });

  it('should render nothing when show is false', async () => {
    const wrapper = await mountModal({ show: false });
    expect(document.body.textContent).not.toContain('Delete rule?');
    wrapper.unmount();
  });

  it('should expose dialog semantics', async () => {
    const wrapper = await mountModal();
    expect(document.querySelector('[role="dialog"]')).not.toBeNull();
    wrapper.unmount();
  });

  it('should render the footer slot', async () => {
    const wrapper = await mountModal(
      {},
      { footer: '<button id="ok">OK</button>' }
    );
    expect(document.querySelector('#ok')).not.toBeNull();
    wrapper.unmount();
  });

  it('should emit update:show false when the close button is clicked', async () => {
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

  it('should hide the close button when closable is false', async () => {
    const wrapper = await mountModal({ closable: false });
    expect(document.querySelector('.ab-modal-close')).toBeNull();
    wrapper.unmount();
  });

  it('should keep the outer modal open when clicking inside a nested modal', async () => {
    const Host = defineComponent({
      components: { AbModal },
      setup() {
        const outer = ref(true);
        const inner = ref(true);
        return { outer, inner };
      },
      template: `
        <AbModal v-model:show="outer" title="outer">
          <p>outer body</p>
          <AbModal v-model:show="inner" title="inner">
            <p id="inner-body">inner body</p>
          </AbModal>
        </AbModal>`,
    });
    const wrapper = mount(Host, { attachTo: document.body });
    await new Promise((resolve) => setTimeout(resolve));

    const innerBody = document.querySelector('#inner-body') as HTMLElement;
    expect(innerBody).not.toBeNull();
    // naive-ui 的 clickoutside 走 pointer/mouse 事件序列
    for (const type of ['pointerdown', 'mousedown', 'click']) {
      innerBody.dispatchEvent(
        new MouseEvent(type, { bubbles: true, cancelable: true })
      );
    }
    await new Promise((resolve) => setTimeout(resolve));

    expect((wrapper.vm as any).outer).toBe(true);
    wrapper.unmount();
  });
});

function pluginInputs(parent: HTMLElement) {
  const host = document.createElement('ab-plugin-focus-test');
  const root = host.attachShadow({ mode: 'open' });
  const nested = document.createElement('div');
  const inner = nested.attachShadow({ mode: 'open' });
  inner.innerHTML = '<input id="first"><input id="last">';
  root.append(nested);
  parent.append(host);
  return { host, inner, first: inner.querySelector<HTMLInputElement>('#first')!, last: inner.querySelector<HTMLInputElement>('#last')! };
}

it('keeps typing focus inside nested plugin shadow roots while retaining the modal trap', async () => {
  const outside = document.createElement('input');
  document.body.append(outside);
  const wrapper = await mountModal({}, { default: '<input id="native"><div id="plugin"></div>' });
  const { host, inner, first } = pluginInputs(document.querySelector('#plugin')!);
  first.focus();
  expect(document.activeElement).toBe(host);
  expect(inner.activeElement).toBe(first);
  first.value = 'editable text';
  first.dispatchEvent(new InputEvent('input', { bubbles: true, composed: true }));
  expect(inner.activeElement).toBe(first);
  expect(first.value).toBe('editable text');
  outside.focus();
  expect(document.activeElement).toBe(document.querySelector('#native'));
  wrapper.unmount();
});

it('wraps both tab boundaries through focusable plugin shadow descendants', async () => {
  const wrapper = await mountModal({ title: '', closable: false }, { default: '<div id="plugin"></div>' });
  const { host, inner, first, last } = pluginInputs(document.querySelector('#plugin')!);
  const guards = document.querySelectorAll<HTMLElement>('div[aria-hidden="true"][tabindex="0"]');
  expect(guards.length).toBe(2);
  // These sentinels receive focus on Shift+Tab / Tab at the dialog boundaries.
  last.focus();
  guards[1].focus();
  expect(document.activeElement).toBe(host);
  expect(inner.activeElement).toBe(first);
  guards[0].focus();
  expect(inner.activeElement).toBe(last);
  wrapper.unmount();
});
