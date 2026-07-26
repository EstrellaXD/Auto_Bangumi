import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AbProgress from '../ab-progress.vue';

describe('ab-progress', () => {
  it('should use a contextual accessible name', () => {
    const wrapper = mount(AbProgress, {
      props: {
        value: 50,
        label: '50%',
        ariaLabel: 'Episode 1 download progress',
      },
    });

    expect(wrapper.get('[role="progressbar"]').attributes('aria-label')).toBe(
      'Episode 1 download progress'
    );
  });

  it('should keep the compact visible label when given a contextual name', () => {
    const wrapper = mount(AbProgress, {
      props: {
        value: 50,
        label: '50%',
        ariaLabel: 'Episode 1 download progress',
      },
    });

    expect(wrapper.get('.ab-progress-label').text()).toBe('50%');
  });
});
