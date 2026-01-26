/**
 * Tests for AbSwitch component
 */

import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { h, defineComponent, ref } from 'vue';
import AbSwitch from '../ab-switch.vue';

// Mock @headlessui/vue Switch component
vi.mock('@headlessui/vue', () => ({
  Switch: defineComponent({
    props: ['modelValue', 'as'],
    emits: ['update:modelValue'],
    setup(props, { emit, slots }) {
      const toggle = () => {
        emit('update:modelValue', !props.modelValue);
      };
      return () =>
        h(
          'div',
          {
            class: 'headlessui-switch-mock',
            onClick: toggle,
            'data-checked': props.modelValue,
          },
          slots.default?.()
        );
    },
  }),
}));

describe('AbSwitch', () => {
  describe('rendering', () => {
    it('should render switch track', () => {
      const wrapper = mount(AbSwitch);

      expect(wrapper.find('.switch-track').exists()).toBe(true);
    });

    it('should render switch thumb', () => {
      const wrapper = mount(AbSwitch);

      expect(wrapper.find('.switch-thumb').exists()).toBe(true);
    });
  });

  describe('checked state', () => {
    it('should be unchecked by default', () => {
      const wrapper = mount(AbSwitch);
      const track = wrapper.find('.switch-track');
      const thumb = wrapper.find('.switch-thumb');

      expect(track.classes()).not.toContain('switch-track--checked');
      expect(thumb.classes()).not.toContain('switch-thumb--checked');
    });

    it('should apply checked classes when checked is true', async () => {
      const wrapper = mount(AbSwitch, {
        props: {
          checked: true,
          'onUpdate:checked': (e: boolean) =>
            wrapper.setProps({ checked: e }),
        },
      });

      const track = wrapper.find('.switch-track');
      const thumb = wrapper.find('.switch-thumb');

      expect(track.classes()).toContain('switch-track--checked');
      expect(thumb.classes()).toContain('switch-thumb--checked');
    });

    it('should not have checked classes when checked is false', () => {
      const wrapper = mount(AbSwitch, {
        props: {
          checked: false,
          'onUpdate:checked': () => {},
        },
      });

      const track = wrapper.find('.switch-track');
      const thumb = wrapper.find('.switch-thumb');

      expect(track.classes()).not.toContain('switch-track--checked');
      expect(thumb.classes()).not.toContain('switch-thumb--checked');
    });
  });

  describe('v-model', () => {
    it('should emit update:checked when toggled', async () => {
      const wrapper = mount(AbSwitch, {
        props: {
          checked: false,
          'onUpdate:checked': (e: boolean) =>
            wrapper.setProps({ checked: e }),
        },
      });

      // Find the HeadlessUI Switch mock and click it
      const switchMock = wrapper.find('.headlessui-switch-mock');
      await switchMock.trigger('click');

      expect(wrapper.emitted('update:checked')).toBeTruthy();
    });

    it('should toggle from false to true', async () => {
      let checked = false;
      const wrapper = mount(AbSwitch, {
        props: {
          checked,
          'onUpdate:checked': (e: boolean) => {
            checked = e;
            wrapper.setProps({ checked: e });
          },
        },
      });

      const switchMock = wrapper.find('.headlessui-switch-mock');
      await switchMock.trigger('click');

      expect(checked).toBe(true);
    });

    it('should toggle from true to false', async () => {
      let checked = true;
      const wrapper = mount(AbSwitch, {
        props: {
          checked,
          'onUpdate:checked': (e: boolean) => {
            checked = e;
            wrapper.setProps({ checked: e });
          },
        },
      });

      const switchMock = wrapper.find('.headlessui-switch-mock');
      await switchMock.trigger('click');

      expect(checked).toBe(false);
    });
  });

  describe('accessibility', () => {
    it('should use HeadlessUI Switch component', () => {
      const wrapper = mount(AbSwitch);

      // The mock creates a div with this class
      expect(wrapper.find('.headlessui-switch-mock').exists()).toBe(true);
    });
  });

  describe('styling', () => {
    it('should have correct track dimensions via CSS class', () => {
      const wrapper = mount(AbSwitch);
      const track = wrapper.find('.switch-track');

      expect(track.exists()).toBe(true);
      expect(track.classes()).toContain('switch-track');
    });

    it('should have correct thumb styling via CSS class', () => {
      const wrapper = mount(AbSwitch);
      const thumb = wrapper.find('.switch-thumb');

      expect(thumb.exists()).toBe(true);
      expect(thumb.classes()).toContain('switch-thumb');
    });
  });
});
