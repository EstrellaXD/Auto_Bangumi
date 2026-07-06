import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbInput from '../ab-input.vue';

describe('ab-input', () => {
  it('should bind v-model', async () => {
    const wrapper = mount(AbInput, {
      props: {
        modelValue: 'abc',
        'onUpdate:modelValue': (v: string) =>
          wrapper.setProps({ modelValue: v }),
      },
    });
    await wrapper.find('input').setValue('https://mikanani.me');
    expect(wrapper.props('modelValue')).toBe('https://mikanani.me');
  });

  it('should apply the error class when error is set', () => {
    const wrapper = mount(AbInput, {
      props: { modelValue: '', error: true },
    });
    expect(wrapper.classes()).toContain('ab-input--error');
  });

  it('should clear the value via the clear button when clearable', async () => {
    const wrapper = mount(AbInput, {
      props: {
        modelValue: 'abc',
        clearable: true,
        'onUpdate:modelValue': (v: string) =>
          wrapper.setProps({ modelValue: v }),
      },
    });
    await wrapper.find('.ab-input-clear').trigger('click');
    expect(wrapper.props('modelValue')).toBe('');
  });

  it('should toggle password visibility', async () => {
    const wrapper = mount(AbInput, {
      props: { modelValue: 'secret', type: 'password' },
    });
    expect(wrapper.find('input').attributes('type')).toBe('password');
    await wrapper.find('.ab-input-reveal').trigger('click');
    expect(wrapper.find('input').attributes('type')).toBe('text');
  });

  it('should emit numbers for type=number', async () => {
    const wrapper = mount(AbInput, {
      props: { modelValue: 0, type: 'number' },
    });
    await wrapper.find('input').setValue('42');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([42]);
  });
});
