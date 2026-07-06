import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbTag from '../ab-tag.vue';

describe('ab-tag', () => {
  it('renders the title text', () => {
    const wrapper = mount(AbTag, {
      props: { type: 'success', title: '葬送的芙莉莲 第二季' },
    });
    expect(wrapper.text()).toContain('葬送的芙莉莲 第二季');
  });

  it('applies the semantic type class', () => {
    const wrapper = mount(AbTag, {
      props: { type: 'warning', title: 'Needs review' },
    });
    expect(wrapper.classes()).toContain('ab-tag--warning');
  });

  it('does not render a close control by default', () => {
    const wrapper = mount(AbTag, { props: { type: 'info', title: 'S02E08' } });
    expect(wrapper.find('.ab-tag-close').exists()).toBe(false);
  });

  it('emits close when the close control is clicked', async () => {
    const wrapper = mount(AbTag, {
      props: { type: 'info', title: 'S02E08', closable: true },
    });
    await wrapper.find('.ab-tag-close').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
