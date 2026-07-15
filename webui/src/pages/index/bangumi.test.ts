import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { defineComponent, ref } from 'vue';
import type { Component } from 'vue';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBangumiStore } from '@/store/bangumi';
import { mockBangumiRule } from '@/test/mocks/api';

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

vi.mock('@/hooks/useAddRss', () => ({
  useAddRss: () => ({ openAddRss: vi.fn() }),
}));

const MenuStub = defineComponent({
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
  template: `
    <div class="menu-stub">
      <slot name="trigger" />
      <span v-for="item in items" :key="item.key">
        {{ typeof item.label === 'function' ? item.label() : item.label }}
      </span>
    </div>
  `,
});

describe('Bangumi page mobile actions', () => {
  let BangumiPage: Component;

  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    vi.stubGlobal('useRouter', () => ({ push: vi.fn() }));
    BangumiPage = (await import('./bangumi.vue')).default;
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    isMobile.value = true;
    useBangumiStore().bangumi = [{ ...mockBangumiRule }];
  });

  function mountPage() {
    return mount(BangumiPage, {
      global: {
        stubs: {
          'ab-pull-refresh': { template: '<div><slot /></div>' },
          'ab-bangumi-card': true,
          'ab-menu': MenuStub,
          'ab-icon-button': { template: '<button><slot /></button>' },
          'ab-button': { template: '<button><slot /></button>' },
          'ab-modal': { template: '<div><slot /></div>' },
          'ab-badge': true,
          'ab-tag': true,
        },
      },
    });
  }

  it('should keep refresh posters reachable from a local disclosure on mobile', () => {
    const wrapper = mountPage();

    expect(wrapper.get('.bangumi-mobile-toolbar').text()).toContain(
      'topbar.refresh_poster'
    );
  });

  it('should preserve the existing desktop surface without the mobile disclosure', () => {
    isMobile.value = false;

    const wrapper = mountPage();

    expect(wrapper.find('.bangumi-mobile-toolbar').exists()).toBe(false);
  });
});
