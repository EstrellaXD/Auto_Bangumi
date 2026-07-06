import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbIconButton from '../ab-icon-button.vue';

describe('ab-icon-button', () => {
  it('exposes the label as aria-label', () => {
    const wrapper = mount(AbIconButton, { props: { label: 'Delete rule' } });
    expect(wrapper.attributes('aria-label')).toBe('Delete rule');
  });

  it('emits click when clicked', async () => {
    const wrapper = mount(AbIconButton, { props: { label: 'Edit' } });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('does not emit click when disabled', async () => {
    const wrapper = mount(AbIconButton, {
      props: { label: 'Edit', disabled: true },
    });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });
});
