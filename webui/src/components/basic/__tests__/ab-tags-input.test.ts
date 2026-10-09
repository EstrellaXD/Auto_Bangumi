import { mount } from '@vue/test-utils';
import AbTagsInput from '../ab-tags-input.vue';

describe('ab-tags-input', () => {
  it('should add a trimmed tag on Enter and ignore duplicates', async () => {
    const wrapper = mount(AbTagsInput, {
      props: { modelValue: ['a'], ariaLabel: 'Tags' },
      global: { mocks: { $t: (k: string) => k } },
    });
    const input = wrapper.find('input');
    expect(input.attributes('aria-label')).toBe('Tags');

    await input.setValue(' b ');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['a', 'b']]);

    await input.setValue('a');
    await input.trigger('keydown', { key: 'Enter' });
    expect(wrapper.emitted('update:modelValue')).toHaveLength(1);
  });

  it('should remove a tag when its close button is clicked', async () => {
    const wrapper = mount(AbTagsInput, {
      props: { modelValue: ['a', 'b'] },
      global: { mocks: { $t: (k: string) => k } },
    });
    await wrapper.find('.ab-tag-close').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['b']]);
  });
});
