import { describe, expect, it } from 'vitest';
import { defineComponent, h, inject } from 'vue';
import { mount } from '@vue/test-utils';
import AbField, { abFieldInjectionKey } from '../ab-field.vue';

// A control that reads the field context the way ab-input/ab-select do
const FakeControl = defineComponent({
  setup() {
    const field = inject(abFieldInjectionKey, null);
    return () =>
      h('input', {
        id: field?.controlId,
        'aria-describedby': field?.describedBy.value,
        'aria-invalid': field?.invalid.value || undefined,
      });
  },
});

function mountField(props = {}) {
  return mount(AbField, {
    props: { label: 'RSS link', ...props },
    slots: { default: FakeControl },
  });
}

describe('ab-field', () => {
  it('associates the label with the control via for/id', () => {
    const wrapper = mountField();
    const label = wrapper.find('label');
    const input = wrapper.find('input');
    expect(label.attributes('for')).toBeTruthy();
    expect(label.attributes('for')).toBe(input.attributes('id'));
  });

  it('shows a required marker when required', () => {
    const wrapper = mountField({ required: true });
    expect(wrapper.find('.ab-field-required').exists()).toBe(true);
  });

  it('wires description and error into aria-describedby', () => {
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

  it('marks the control invalid when error is set', () => {
    const wrapper = mountField({ error: 'Must be a URL' });
    expect(wrapper.find('input').attributes('aria-invalid')).toBe('true');
  });
});
