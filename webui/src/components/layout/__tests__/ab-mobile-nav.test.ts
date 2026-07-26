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
  emits: ['restore-trigger-focus'],
  template:
    '<button class="more-sheet-stub" :data-show="show" @click="$emit(\'restore-trigger-focus\')" />',
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

  it('should focus the More trigger when the sheet requests restoration', async () => {
    const wrapper = mountNav();
    const moreButton = wrapper.find<HTMLButtonElement>(
      'button.mobile-nav__item'
    );
    const focus = vi.spyOn(moreButton.element, 'focus');

    await wrapper.find('button.more-sheet-stub').trigger('click');

    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('should clear More when the mobile nav unmounts at the tablet breakpoint', () => {
    const wrapper = mountNav();
    useMobileShellStore().openOverlay('more');

    wrapper.unmount();

    expect(useMobileShellStore().activeOverlay).toBeNull();
  });

  it('should keep More closed after a mobile breakpoint round trip', () => {
    const wrapper = mountNav();
    useMobileShellStore().openOverlay('more');

    wrapper.unmount();
    const remountedWrapper = mountNav();

    expect(
      remountedWrapper.find('.more-sheet-stub').attributes('data-show')
    ).toBe('false');
  });
});
