import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { defineComponent } from 'vue';
import type { Component } from 'vue';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBangumiStore } from '@/store/bangumi';
import { mockBangumiRule } from '@/test/mocks/api';

vi.mock('@/utils/axios', () => ({
  axios: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/hooks/useBreakpointQuery', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  return {
    useBreakpointQuery: () => ({ isMobile: ref(false) }),
  };
});

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string) => key,
    returnUserLangMsg: () => '',
  }),
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn() }),
}));

const CalendarBoardStub = defineComponent({
  name: 'CalendarBoard',
  props: {
    groupedByDay: {
      type: Object,
      required: true,
    },
  },
  template: '<div data-testid="calendar-board" />',
});

const CalendarRuleListPopupStub = {
  props: {
    show: Boolean,
    group: Object,
  },
  emits: ['update:show', 'select', 'after-leave'],
  template: '<div v-if="show" data-testid="calendar-rule-list" />',
};

describe('Calendar page', () => {
  let CalendarPage: Component;

  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    CalendarPage = (await import('./calendar.vue')).default;
  });

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  function mountCalendar() {
    return mount(CalendarPage, {
      global: {
        stubs: {
          'ab-icon-button': true,
          'calendar-board': CalendarBoardStub,
          'calendar-mobile-list': true,
          'calendar-rule-list-popup': CalendarRuleListPopupStub,
        },
      },
    });
  }

  it('excludes archived rules from weekday groups', () => {
    const store = useBangumiStore();
    store.bangumi = [
      { ...mockBangumiRule, id: 1, air_weekday: 0, archived: false },
      { ...mockBangumiRule, id: 2, air_weekday: 0, archived: true },
    ];

    const wrapper = mountCalendar();
    const groupedByDay = wrapper
      .getComponent(CalendarBoardStub)
      .props('groupedByDay') as Record<
      string,
      Array<{ rules: Array<{ id: number }> }>
    >;

    expect(
      groupedByDay.mon.flatMap((group) => group.rules.map((rule) => rule.id))
    ).toEqual([1]);
  });

  it('shows the empty state when every rule is archived', () => {
    const store = useBangumiStore();
    store.bangumi = [
      { ...mockBangumiRule, id: 1, air_weekday: 0, archived: true },
    ];

    const wrapper = mountCalendar();

    expect(wrapper.find('[data-testid="calendar-board"]').exists()).toBe(false);
    expect(wrapper.find('.empty-guide').exists()).toBe(true);
  });

  it('should open rule editing only after the calendar rule list finishes leaving', async () => {
    const store = useBangumiStore();
    const firstRule = { ...mockBangumiRule, id: 1, air_weekday: 0 };
    store.bangumi = [
      firstRule,
      { ...mockBangumiRule, id: 2, air_weekday: 0, group_name: 'Second' },
    ];
    const wrapper = mountCalendar();
    const board = wrapper.getComponent(CalendarBoardStub);
    const group = (
      board.props('groupedByDay') as Record<
        string,
        Array<{ rules: typeof store.bangumi }>
      >
    ).mon[0];

    board.vm.$emit('card-click', group);
    await wrapper.vm.$nextTick();
    const popup = wrapper.getComponent(CalendarRuleListPopupStub);
    popup.vm.$emit('select', firstRule);
    await wrapper.vm.$nextTick();
    const beforeLeave = store.editRule.show;
    popup.vm.$emit('after-leave');
    await wrapper.vm.$nextTick();

    expect({ beforeLeave, afterLeave: store.editRule.show }).toEqual({
      beforeLeave: false,
      afterLeave: true,
    });
  });
});
