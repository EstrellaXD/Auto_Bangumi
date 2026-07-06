import { describe, expect, it } from 'vitest';
import { defineComponent, h, inject } from 'vue';
import { mount } from '@vue/test-utils';
import AbField, { abFieldInjectionKey } from '../ab-field.vue';

// A control that reads the field context the way ab-input does
const FakeControl = defineComponent({
  setup() {
    const field = inject(abFieldInjectionKey, null);
    // 与 ab-input 相同：认领 controlId，字段才渲染真正的 <label for>
    if (field) field.adopted.value = true;
    return () =>
      h('input', {
        id: field?.controlId,
        'aria-describedby': field?.describedBy.value,
        'aria-invalid': field?.invalid.value || undefined,
      });
  },
});

// naive-ui 类控件：不认领 id
const OpaqueControl = defineComponent({
  setup() {
    return () => h('div', { class: 'fake-select' });
  },
});

function mountField(props = {}) {
  return mount(AbField, {
    props: { label: 'RSS link', ...props },
    slots: { default: FakeControl },
  });
}

describe('ab-field', () => {
  it('should associate the label with the control via for/id', async () => {
    const wrapper = mountField();
    // 控件在挂载期认领 id，label 在下一个 tick 升级为 <label for>
    await wrapper.vm.$nextTick();
    const label = wrapper.find('label');
    const input = wrapper.find('input');
    expect(label.attributes('for')).toBeTruthy();
    expect(label.attributes('for')).toBe(input.attributes('id'));
  });

  it('should render a span instead of label[for] when the control cannot take an id', () => {
    const wrapper = mount(AbField, {
      props: { label: 'Parser' },
      slots: { default: OpaqueControl },
    });
    expect(wrapper.find('label').exists()).toBe(false);
    expect(wrapper.find('.ab-field-label').attributes('for')).toBeUndefined();
  });

  it('should show a required marker when required', () => {
    const wrapper = mountField({ required: true });
    expect(wrapper.find('.ab-field-required').exists()).toBe(true);
  });

  it('should wire description and error into aria-describedby', () => {
    const wrapper = mountField({
      description: 'Mikan personal feed.',
      error: 'Must be a URL',
    });
    const described = wrapper.find('input').attributes('aria-describedby');
    expect(described).toBeTruthy();
    for (const id of described!.split(' ')) {
      expect(wrapper.find(`#${id}`).exists()).toBe(true);
    }
    expect(wrapper.text()).toContain('Mikan personal feed.');
    expect(wrapper.text()).toContain('Must be a URL');
  });

  it('should mark the control invalid when error is set', () => {
    const wrapper = mountField({ error: 'Must be a URL' });
    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true');
  });
});
