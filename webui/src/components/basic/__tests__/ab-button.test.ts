import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbButton from '../ab-button.vue';

describe('ab-button', () => {
  it('renders default slot content', () => {
    const wrapper = mount(AbButton, { slots: { default: 'Add RSS' } });
    expect(wrapper.text()).toContain('Add RSS');
  });

  it('emits click when clicked', async () => {
    const wrapper = mount(AbButton);
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('does not emit click when disabled', async () => {
    const wrapper = mount(AbButton, { props: { disabled: true } });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });

  it('disables the button and shows a spinner when loading', async () => {
    const wrapper = mount(AbButton, { props: { loading: true } });
    expect(wrapper.attributes('disabled')).toBeDefined();
    expect(wrapper.find('.ab-btn-spin').exists()).toBe(true);
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });

  it('applies the variant class', () => {
    const wrapper = mount(AbButton, { props: { variant: 'danger' } });
    expect(wrapper.classes()).toContain('ab-btn--danger');
  });

  it('defaults to type="button" so it does not submit forms', () => {
    const wrapper = mount(AbButton);
    expect(wrapper.attributes('type')).toBe('button');
  });
});
