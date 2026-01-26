/**
 * Tests for AbButton component
 */

import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { h, defineComponent } from 'vue';
import AbButton from '../ab-button.vue';

// Mock naive-ui NSpin component
vi.mock('naive-ui', () => ({
  NSpin: defineComponent({
    props: ['show', 'size'],
    setup(props, { slots }) {
      return () => h('div', { class: 'n-spin-mock' }, slots.default?.());
    },
  }),
}));

describe('AbButton', () => {
  describe('rendering', () => {
    it('should render as button by default', () => {
      const wrapper = mount(AbButton, {
        slots: {
          default: 'Click me',
        },
      });

      expect(wrapper.element.tagName).toBe('BUTTON');
      expect(wrapper.text()).toContain('Click me');
    });

    it('should render as anchor when link is provided', () => {
      const wrapper = mount(AbButton, {
        props: {
          link: 'https://example.com',
        },
        slots: {
          default: 'Click me',
        },
      });

      expect(wrapper.element.tagName).toBe('A');
      expect(wrapper.attributes('href')).toBe('https://example.com');
    });

    it('should render slot content', () => {
      const wrapper = mount(AbButton, {
        slots: {
          default: '<span>Custom Content</span>',
        },
      });

      expect(wrapper.html()).toContain('Custom Content');
    });
  });

  describe('props', () => {
    describe('type', () => {
      it('should have primary type by default', () => {
        const wrapper = mount(AbButton);

        expect(wrapper.classes()).toContain('btn--primary');
      });

      it('should apply secondary type class', () => {
        const wrapper = mount(AbButton, {
          props: { type: 'secondary' },
        });

        expect(wrapper.classes()).toContain('btn--secondary');
      });

      it('should apply warn type class', () => {
        const wrapper = mount(AbButton, {
          props: { type: 'warn' },
        });

        expect(wrapper.classes()).toContain('btn--warn');
      });
    });

    describe('size', () => {
      it('should have normal size by default', () => {
        const wrapper = mount(AbButton);

        expect(wrapper.classes()).toContain('btn--normal');
      });

      it('should apply big size class', () => {
        const wrapper = mount(AbButton, {
          props: { size: 'big' },
        });

        expect(wrapper.classes()).toContain('btn--big');
      });

      it('should apply small size class', () => {
        const wrapper = mount(AbButton, {
          props: { size: 'small' },
        });

        expect(wrapper.classes()).toContain('btn--small');
      });
    });

    describe('loading', () => {
      it('should be false by default', () => {
        const wrapper = mount(AbButton);

        // Verify component renders with default loading=false
        expect(wrapper.vm.$props.loading).toBe(false);
      });
    });
  });

  describe('events', () => {
    it('should emit click event when clicked', async () => {
      const wrapper = mount(AbButton);

      await wrapper.trigger('click');

      expect(wrapper.emitted('click')).toBeTruthy();
      expect(wrapper.emitted('click')?.length).toBe(1);
    });

    it('should emit click event multiple times', async () => {
      const wrapper = mount(AbButton);

      await wrapper.trigger('click');
      await wrapper.trigger('click');
      await wrapper.trigger('click');

      expect(wrapper.emitted('click')?.length).toBe(3);
    });
  });

  describe('accessibility', () => {
    it('should have btn class for styling', () => {
      const wrapper = mount(AbButton);

      expect(wrapper.classes()).toContain('btn');
    });
  });

  describe('combined props', () => {
    it('should apply multiple props correctly', () => {
      const wrapper = mount(AbButton, {
        props: {
          type: 'warn',
          size: 'big',
        },
        slots: {
          default: 'Delete',
        },
      });

      expect(wrapper.classes()).toContain('btn--warn');
      expect(wrapper.classes()).toContain('btn--big');
      expect(wrapper.text()).toContain('Delete');
    });
  });
});
