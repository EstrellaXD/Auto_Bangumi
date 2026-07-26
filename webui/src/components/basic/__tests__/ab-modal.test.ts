import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { defineComponent, ref } from 'vue';
import type { Component } from 'vue';
import { mount } from '@vue/test-utils';
import { TransitionRoot } from '@headlessui/vue';
import AbBottomSheet from '../ab-bottom-sheet.vue';

const isMobile = ref(false);

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile }),
}));

let AbModal: Component;

beforeAll(async () => {
  AbModal = (await import('../ab-modal.vue')).default;
});

beforeEach(() => {
  isMobile.value = false;
});

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
    const wrapper = await mountModal(
      { closable: false },
      { default: '<button type="button">body action</button>' }
    );
    expect(document.querySelector('.ab-modal-close')).toBeNull();
    wrapper.unmount();
  });

  it('should emit after-leave when the desktop dialog finishes leaving', async () => {
    const wrapper = await mountModal();
    const desktopRenderer = wrapper.getComponent(TransitionRoot);

    await wrapper.setProps({ show: false });
    desktopRenderer.vm.$emit('afterLeave');
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('after-leave')).toHaveLength(1);
    wrapper.unmount();
  });

  it('should forward after-leave when the mobile sheet finishes leaving', async () => {
    isMobile.value = true;
    const wrapper = await mountModal();

    await wrapper.setProps({ show: false });
    wrapper.getComponent(AbBottomSheet).vm.$emit('after-leave');
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('after-leave')).toHaveLength(1);
    wrapper.unmount();
  });

  it('should apply an optional desktop max width when provided', async () => {
    const wrapper = await mountModal({ desktopMaxWidth: '460px' });

    expect(
      document.querySelector<HTMLElement>('.ab-modal-panel')?.style.maxWidth
    ).toBe('460px');
    wrapper.unmount();
  });

  it('should ignore the desktop max width when rendering a mobile sheet', async () => {
    isMobile.value = true;
    const wrapper = await mountModal({ desktopMaxWidth: '460px' });

    expect(
      document.querySelector<HTMLElement>('[data-testid="bottom-sheet-panel"]')
        ?.style.maxWidth
    ).toBe('');
    wrapper.unmount();
  });

  it('should finish a desktop close cycle before adopting the mobile renderer', async () => {
    const wrapper = await mountModal();
    const desktopRenderer = wrapper.getComponent(TransitionRoot);

    await wrapper.setProps({ show: false });
    isMobile.value = true;
    await wrapper.vm.$nextTick();
    const rendererDuringLeave = wrapper.findComponent(AbBottomSheet).exists()
      ? 'mobile'
      : 'desktop';
    desktopRenderer.vm.$emit('afterLeave');
    desktopRenderer.vm.$emit('afterLeave');
    await wrapper.vm.$nextTick();
    const afterLeaveCount = wrapper.emitted('after-leave')?.length ?? 0;

    await wrapper.setProps({ show: true });
    await new Promise((resolve) => setTimeout(resolve));
    const rendererOnNextOpen = wrapper.findComponent(AbBottomSheet).exists()
      ? 'mobile'
      : 'desktop';

    expect({
      rendererDuringLeave,
      afterLeaveCount,
      rendererOnNextOpen,
    }).toEqual({
      rendererDuringLeave: 'desktop',
      afterLeaveCount: 1,
      rendererOnNextOpen: 'mobile',
    });
    wrapper.unmount();
  });

  it('should finish a mobile close cycle before adopting the desktop renderer', async () => {
    isMobile.value = true;
    const wrapper = await mountModal();
    const mobileRenderer = wrapper.getComponent(AbBottomSheet);

    await wrapper.setProps({ show: false });
    isMobile.value = false;
    await wrapper.vm.$nextTick();
    const rendererDuringLeave = wrapper.findComponent(AbBottomSheet).exists()
      ? 'mobile'
      : 'desktop';
    mobileRenderer.vm.$emit('after-leave');
    mobileRenderer.vm.$emit('after-leave');
    await wrapper.vm.$nextTick();
    const afterLeaveCount = wrapper.emitted('after-leave')?.length ?? 0;

    await wrapper.setProps({ show: true });
    await new Promise((resolve) => setTimeout(resolve));
    const rendererOnNextOpen = wrapper.findComponent(AbBottomSheet).exists()
      ? 'mobile'
      : 'desktop';

    expect({
      rendererDuringLeave,
      afterLeaveCount,
      rendererOnNextOpen,
    }).toEqual({
      rendererDuringLeave: 'mobile',
      afterLeaveCount: 1,
      rendererOnNextOpen: 'desktop',
    });
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
    // Native Node.contains(null) returns false; happy-dom 12 throws instead.
    const nativeContains = Node.prototype.contains;
    const contains = vi
      .spyOn(Node.prototype, 'contains')
      .mockImplementation(function (this: Node, node: Node | null) {
        return node == null ? false : nativeContains.call(this, node);
      });
    // headlessui 的 outside-click 走 pointer/mouse 事件序列
    for (const type of ['pointerdown', 'mousedown', 'click']) {
      innerBody.dispatchEvent(
        new MouseEvent(type, { bubbles: true, cancelable: true })
      );
    }
    contains.mockRestore();
    await new Promise((resolve) => setTimeout(resolve));

    expect((wrapper.vm as any).outer).toBe(true);
    wrapper.unmount();
  });
});
