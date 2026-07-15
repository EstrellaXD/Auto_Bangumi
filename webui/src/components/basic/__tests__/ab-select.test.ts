import { readFileSync } from 'node:fs';
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

  it('should give teleported select options a strict mobile touch target', () => {
    const globalStyles = readFileSync(
      new URL('../../../style/global.scss', import.meta.url),
      'utf8'
    );

    expect(globalStyles).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.n-base-select-option[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });
});
