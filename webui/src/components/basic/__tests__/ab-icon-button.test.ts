import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AbIconButton from '../ab-icon-button.vue';

describe('ab-icon-button', () => {
  it('should expose the label as aria-label', () => {
    const wrapper = mount(AbIconButton, { props: { label: 'Delete rule' } });
    expect(wrapper.attributes('aria-label')).toBe('Delete rule');
  });

  it('should emit click when clicked', async () => {
    const wrapper = mount(AbIconButton, { props: { label: 'Edit' } });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('should not emit click when disabled', async () => {
    const wrapper = mount(AbIconButton, {
      props: { label: 'Edit', disabled: true },
    });
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeUndefined();
  });

  it('should enforce a 44 pixel target below 640 pixels for every size', () => {
    const source = readFileSync(
      new URL('../ab-icon-button.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?&--md,[\s\S]*?&--sm\s*\{[\s\S]*?width:\s*var\(--touch-target\)[\s\S]*?height:\s*var\(--touch-target\)/
    );
  });
});
