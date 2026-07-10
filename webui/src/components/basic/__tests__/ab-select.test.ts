import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { NSelect } from 'naive-ui';
import AbSelect from '../ab-select.vue';

describe('ab-select', () => {
  it('wires combobox, listbox, and option semantics through naive-ui', () => {
    const wrapper = mount(AbSelect, {
      props: {
        ariaLabel: 'Language',
        items: ['zh', 'jp'],
      },
    });
    const select = wrapper.findComponent(NSelect);

    expect(select.attributes('role')).toBe('combobox');
    expect(select.attributes('aria-haspopup')).toBe('listbox');
    expect(select.props('menuProps')).toMatchObject({ role: 'listbox' });
    const nodeProps = select.props('nodeProps');
    expect(nodeProps).toBeTypeOf('function');
    if (!nodeProps) throw new Error('nodeProps should be configured');
    expect(nodeProps({ label: 'jp', value: 'jp' })).toEqual({
      role: 'option',
    });
  });
});
