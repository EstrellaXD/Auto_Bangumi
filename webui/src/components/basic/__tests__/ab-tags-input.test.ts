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

  // blur 不冒泡，组件根节点上的监听收不到；focusout 才会从 input 冒泡上来
  it('should add the typed tag when the input loses focus', async () => {
    const wrapper = mount(AbTagsInput, {
      props: { modelValue: [] },
      global: { mocks: { $t: (k: string) => k } },
    });
    const input = wrapper.find('input');
    await input.setValue('c');
    await input.trigger('focusout');
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([['c']]);
  });

  it.each([{ isComposing: true }, { keyCode: 229 }])(
    'should ignore Enter during IME composition (%j)',
    async (init) => {
      const wrapper = mount(AbTagsInput, {
        props: { modelValue: [] },
        global: { mocks: { $t: (k: string) => k } },
      });
      const input = wrapper.find('input');
      await input.setValue('ni');
      await input.trigger('keydown', { key: 'Enter', ...init });
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
    }
  );
});
