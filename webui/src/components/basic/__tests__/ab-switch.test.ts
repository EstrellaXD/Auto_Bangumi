import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AbSwitch from '../ab-switch.vue';

describe('ab-switch', () => {
  it('should put the mobile touch-target class on the rendered switch root', () => {
    const wrapper = mount(AbSwitch);

    expect(wrapper.get('.n-switch').classes()).toContain('ab-switch');
  });
});
