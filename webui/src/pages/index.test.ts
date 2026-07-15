/* eslint-disable vue/one-component-per-file */
import { defineComponent, ref } from 'vue';
import type { Component } from 'vue';
import { mount } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';

vi.mock('pinia', () => ({
  storeToRefs: () => ({
    editRule: ref({ show: false, item: {} }),
  }),
}));

vi.mock('@/store/bangumi', () => ({
  useBangumiStore: () => ({
    archiveRule: vi.fn(),
    editRule: { show: false, item: {} },
    enableRule: vi.fn(),
    ruleManage: vi.fn(),
    unarchiveRule: vi.fn(),
    updateRule: vi.fn(),
  }),
}));

const HomeStub = defineComponent({
  name: 'HomeStub',
  template: '<section><h1>Runtime overview</h1></section>',
});

const RouterViewStub = defineComponent({
  name: 'RouterView',
  setup() {
    return { HomeStub };
  },
  template: '<slot :Component="HomeStub" />',
});

const PageTitleStub = defineComponent({
  name: 'AbPageTitle',
  props: { title: String },
  template: '<h1 data-page-title>{{ title }}</h1>',
});

let IndexPage: Component;

describe('authenticated layout', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    IndexPage = (await import('./index.vue')).default;
  });

  it('should render one page heading when the Home route supplies its own heading', () => {
    const wrapper = mount(IndexPage, {
      global: {
        mocks: {
          $route: { name: 'Home' },
        },
        stubs: {
          AbEditRule: true,
          AbPageTitle: PageTitleStub,
          AbSidebar: true,
          AbTopbar: true,
          KeepAlive: false,
          RouterView: RouterViewStub,
          Transition: false,
        },
      },
    });

    expect(wrapper.findAll('h1')).toHaveLength(1);
  });
});
