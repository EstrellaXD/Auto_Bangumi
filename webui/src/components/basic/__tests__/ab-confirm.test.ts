import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbConfirmHost from '../ab-confirm-host.vue';
import { useConfirm } from '@/hooks/useConfirm';

async function tick() {
  await new Promise((resolve) => setTimeout(resolve));
}

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
