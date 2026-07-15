/* eslint-disable vue/one-component-per-file */
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { defineComponent, ref } from 'vue';
import type { Component } from 'vue';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRSSStore } from '@/store/rss';
import { mockRSSItem } from '@/test/mocks/api';

const isMobile = ref(true);

vi.mock('@/utils/axios', () => ({
  axios: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string) => key,
    returnUserLangMsg: () => '',
  }),
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn() }),
}));

vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

const ContainerStub = defineComponent({
  template:
    '<div class="container-stub"><slot name="title-right" /><slot /></div>',
});

const ButtonStub = defineComponent({
  emits: ['click'],
  template:
    '<button @click="$emit(\'click\', $event)"><slot name="icon" /><slot /></button>',
});

const DataTableStub = defineComponent({
  name: 'NDataTable',
  props: {
    checkedRowKeys: {
      type: Array,
      default: () => [],
    },
  },
  template: '<div class="data-table-stub" />',
});

describe('RSS page mobile actions', () => {
  let RSSPage: Component;

  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    RSSPage = (await import('./rss.vue')).default;
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    isMobile.value = true;
    const store = useRSSStore();
    store.rss = [{ ...mockRSSItem }];
    store.selectedRSS = [mockRSSItem.id];
  });

  it('should move selected RSS actions into a sticky mobile toolbar', () => {
    const wrapper = mount(RSSPage, {
      global: {
        stubs: {
          'ab-container': ContainerStub,
          'ab-list': true,
          'ab-button': ButtonStub,
          AbButton: ButtonStub,
          'ab-tag': true,
          NDataTable: true,
        },
      },
    });

    expect(
      wrapper.get('.rss-selection-toolbar').findAll('button')
    ).toHaveLength(3);
  });

  it('should preserve selected rows when switching to the desktop table', () => {
    isMobile.value = false;

    const wrapper = mount(RSSPage, {
      global: {
        stubs: {
          'ab-container': ContainerStub,
          'ab-list': true,
          'ab-button': ButtonStub,
          AbButton: ButtonStub,
          'ab-tag': true,
          DataTable: DataTableStub,
        },
      },
    });

    expect(wrapper.getComponent(DataTableStub).props('checkedRowKeys')).toEqual(
      [mockRSSItem.id]
    );
  });
});
