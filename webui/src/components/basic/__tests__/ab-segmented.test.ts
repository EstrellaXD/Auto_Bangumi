import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbSegmented from '../ab-segmented.vue';

const options = [
  { label: 'All', value: 'all' },
  { label: 'Airing', value: 'airing' },
  { label: 'Archived', value: 'archived' },
];

describe('ab-segmented', () => {
  it('marks the selected option', () => {
    const wrapper = mount(AbSegmented, {
      props: { options, value: 'airing' },
    });
    const tabs = wrapper.findAll('[role="tab"]');
    expect(tabs[1].attributes('aria-selected')).toBe('true');
    expect(tabs[0].attributes('aria-selected')).toBe('false');
  });

  it('updates v-model on click', async () => {
    const wrapper = mount(AbSegmented, {
      props: { options, value: 'all' },
    });
    await wrapper.findAll('[role="tab"]')[2].trigger('click');
    expect(wrapper.emitted('update:value')?.[0]).toEqual(['archived']);
  });

  it('moves selection with arrow keys', async () => {
    const wrapper = mount(AbSegmented, {
      props: { options, value: 'all' },
    });
    await wrapper.findAll('[role="tab"]')[0].trigger('keydown', {
      key: 'ArrowRight',
    });
    expect(wrapper.emitted('update:value')?.[0]).toEqual(['airing']);
  });
});
