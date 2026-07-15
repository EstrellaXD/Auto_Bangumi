/* eslint-disable vue/one-component-per-file */
import { defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AbMobileNav from '../ab-mobile-nav.vue';
import { useMobileShellStore } from '@/store/mobile-shell';

vi.mock('../ab-mobile-more-sheet.vue', () => ({
  default: {
    name: 'AbMobileMoreSheet',
    props: ['show'],
    template: '<div class="more-sheet-stub" :data-show="show" />',
  },
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: String, required: true } },
  template: '<a :href="to"><slot /></a>',
});

const MoreSheetStub = defineComponent({
  name: 'AbMobileMoreSheet',
  props: { show: Boolean },
  template: '<div class="more-sheet-stub" :data-show="show" />',
});

function mountNav() {
  return mount(AbMobileNav, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        AbMobileMoreSheet: MoreSheetStub,
      },
    },
  });
}

describe('ab-mobile-nav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render three destinations when the mobile shell is shown', () => {
    const wrapper = mountNav();

    expect(wrapper.findAll('.mobile-nav__item')).toHaveLength(3);
  });

  it('should expose a home route when the mobile shell is shown', () => {
    const wrapper = mountNav();

    expect(wrapper.find('a[href="/home"]').exists()).toBe(true);
  });

  it('should expose a search route when the mobile shell is shown', () => {
    const wrapper = mountNav();

    expect(wrapper.find('a[href="/search"]').exists()).toBe(true);
  });

  it('should open More when the More destination is pressed', async () => {
    const wrapper = mountNav();

    await wrapper.find('button.mobile-nav__item').trigger('click');

    expect(useMobileShellStore().activeOverlay).toBe('more');
  });

  it('should report More as expanded when the More sheet is open', async () => {
    const wrapper = mountNav();
    useMobileShellStore().openOverlay('more');
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('button.mobile-nav__item').attributes('aria-expanded')
    ).toBe('true');
  });
});
