import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import AbConfirmHost from '../ab-confirm-host.vue';
import { useConfirm } from '@/hooks/useConfirm';

async function tick() {
  await new Promise((resolve) => setTimeout(resolve));
}

const ModalStub = defineComponent({
  name: 'AbModal',
  props: { show: Boolean, title: String },
  emits: ['update:show', 'after-leave'],
  template:
    '<section v-if="show"><h2>{{ title }}</h2><slot /><slot name="footer" /></section>',
});

describe('useConfirm + ab-confirm-host', () => {
  it('should resolve true when the confirm button is clicked', async () => {
    const wrapper = mount(AbConfirmHost, { attachTo: document.body });
    const { confirm } = useConfirm();
    const result = confirm({ title: 'Delete rule?', body: 'Files stay.' });
    await tick();
    expect(document.body.textContent).toContain('Delete rule?');

    (document.querySelector('.ab-confirm-ok') as HTMLButtonElement).click();
    await expect(result).resolves.toBe(true);
    wrapper.unmount();
  });

  it('should resolve false when cancelled', async () => {
    const wrapper = mount(AbConfirmHost, { attachTo: document.body });
    const { confirm } = useConfirm();
    const result = confirm({ title: 'Reset log?' });
    await tick();

    (document.querySelector('.ab-confirm-cancel') as HTMLButtonElement).click();
    await expect(result).resolves.toBe(false);
    wrapper.unmount();
  });

  it('should restore the captured trigger after a cancelled dialog leaves', async () => {
    const trigger = document.createElement('button');
    document.body.append(trigger);
    trigger.focus();
    const wrapper = mount(AbConfirmHost, {
      attachTo: document.body,
      global: { stubs: { AbModal: ModalStub } },
    });
    const { confirm } = useConfirm();
    const result = confirm({ title: 'Reset log?' });
    await tick();

    const cancel = document.querySelector(
      '.ab-confirm-cancel'
    ) as HTMLButtonElement;
    cancel.focus();
    cancel.click();
    await result;
    wrapper.getComponent(ModalStub).vm.$emit('after-leave');
    await tick();

    expect(document.activeElement === trigger).toBe(true);
    wrapper.unmount();
    trigger.remove();
  });

  it('should preserve the original trigger when an open confirmation is replaced', async () => {
    const trigger = document.createElement('button');
    document.body.append(trigger);
    trigger.focus();
    const wrapper = mount(AbConfirmHost, {
      attachTo: document.body,
      global: { stubs: { AbModal: ModalStub } },
    });
    const { confirm } = useConfirm();
    const first = confirm({ title: 'First confirmation' });
    await tick();

    const cancel = document.querySelector(
      '.ab-confirm-cancel'
    ) as HTMLButtonElement;
    cancel.focus();
    const second = confirm({ title: 'Replacement confirmation' });
    await expect(first).resolves.toBe(false);
    cancel.click();
    await second;
    wrapper.getComponent(ModalStub).vm.$emit('after-leave');
    await tick();

    expect(document.activeElement === trigger).toBe(true);
    wrapper.unmount();
    trigger.remove();
  });

  it('should preserve the original trigger when a confirmation reopens during leave', async () => {
    const trigger = document.createElement('button');
    document.body.append(trigger);
    trigger.focus();
    const wrapper = mount(AbConfirmHost, {
      attachTo: document.body,
      global: { stubs: { AbModal: ModalStub } },
    });
    const { confirm } = useConfirm();
    const first = confirm({ title: 'First confirmation' });
    await tick();

    const cancel = document.querySelector(
      '.ab-confirm-cancel'
    ) as HTMLButtonElement;
    cancel.focus();
    cancel.click();
    await first;
    const second = confirm({ title: 'Reopened confirmation' });
    await tick();

    (document.querySelector('.ab-confirm-cancel') as HTMLButtonElement).click();
    await second;
    wrapper.getComponent(ModalStub).vm.$emit('after-leave');
    await tick();

    expect(document.activeElement === trigger).toBe(true);
    wrapper.unmount();
    trigger.remove();
  });

  it('should render danger variant confirm button when danger is set', async () => {
    const wrapper = mount(AbConfirmHost, { attachTo: document.body });
    const { confirm } = useConfirm();
    const result = confirm({ title: 'Delete rule?', danger: true });
    await tick();
    const ok = document.querySelector('.ab-confirm-ok') as HTMLButtonElement;
    expect(ok.className).toContain('ab-btn--danger');
    ok.click();
    await result;
    wrapper.unmount();
  });
});
