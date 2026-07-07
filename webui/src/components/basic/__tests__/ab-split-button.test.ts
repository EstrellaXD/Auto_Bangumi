import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbSplitButton from '../ab-split-button.vue';

const options = [
  { label: 'Enable rule', value: 'enable' },
  { label: 'Enable + collect season', value: 'collect' },
];

describe('ab-split-button', () => {
  it('should show the label of the selected value on the main button', () => {
    const wrapper = mount(AbSplitButton, {
      props: { options, value: 'collect' },
    });
    expect(wrapper.find('.ab-split-main').text()).toContain(
      'Enable + collect season'
    );
  });

  it('should emit click with the current value', async () => {
    const wrapper = mount(AbSplitButton, {
      props: { options, value: 'enable' },
    });
    await wrapper.find('.ab-split-main').trigger('click');
    expect(wrapper.emitted('click')?.[0]).toEqual(['enable']);
  });

  it('should update v-model when an option is selected from the menu', async () => {
    const wrapper = mount(AbSplitButton, {
      props: { options, value: 'enable' },
      attachTo: document.body,
    });
    await wrapper.find('.ab-split-arrow').trigger('click');
    await wrapper.findAll('[role="menuitem"]')[1].trigger('click');
    expect(wrapper.emitted('update:value')?.[0]).toEqual(['collect']);
  });

  it('should not emit click while loading', async () => {
    const wrapper = mount(AbSplitButton, {
      props: { options, value: 'enable', loading: true },
    });
    await wrapper.find('.ab-split-main').trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });
});
