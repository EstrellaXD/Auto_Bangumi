import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import CalendarRuleListPopup from '../calendar-rule-list-popup.vue';
import { mockBangumiRule } from '@/test/mocks/api';

const ModalStub = defineComponent({
  emits: ['update:show', 'after-leave'],
  template: '<section><slot /></section>',
});

describe('calendar-rule-list-popup', () => {
  it('should forward after-leave when its modal finishes leaving', async () => {
    const wrapper = mount(CalendarRuleListPopup, {
      props: {
        show: true,
        group: {
          key: 'Test Anime::1',
          primary: mockBangumiRule,
          rules: [mockBangumiRule],
        },
      },
      global: {
        stubs: {
          AbModal: ModalStub,
          AbTag: true,
        },
      },
    });

    wrapper.getComponent(ModalStub).vm.$emit('after-leave');
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('after-leave')).toEqual([[]]);
  });
});
