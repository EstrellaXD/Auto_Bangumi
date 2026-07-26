import { nextTick, reactive, ref } from 'vue';
import type { Component } from 'vue';
import { enableAutoUnmount, shallowMount } from '@vue/test-utils';
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { useBreakpointQuery } from '@/hooks/useBreakpointQuery';
import { useConfirm } from '@/hooks/useConfirm';
import { useConfigStore } from '@/store/config';

enableAutoUnmount(afterEach);

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: vi.fn(),
}));
vi.mock('@/hooks/useConfirm', () => ({ useConfirm: vi.fn() }));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/store/config', () => ({ useConfigStore: vi.fn() }));
vi.mock('@/components/setting/config-normal.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-parser.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-download.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-manage.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-notification.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-proxy.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-network.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-search-provider.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-player.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-llm.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-passkey.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-security.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/config-access.vue', () => ({
  default: { template: '<section />' },
}));
vi.mock('@/components/setting/update-card.vue', () => ({
  default: { template: '<section />' },
}));

const isMobile = ref(true);
const isMobileOrTablet = ref(true);
const configStore = reactive({
  dirtyGroups: ref<string[]>([]),
  getConfig: vi.fn(),
  isDirty: ref(false),
  setConfig: vi.fn(),
});
let ConfigPage: Component;

function mountConfig() {
  return shallowMount(ConfigPage, {
    global: {
      stubs: {
        AbButton: true,
        AbInput: {
          props: ['modelValue', 'ariaLabel'],
          template:
            '<input :aria-label="ariaLabel" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
      },
    },
  });
}

describe('config mobile navigation', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    vi.stubGlobal('onBeforeRouteLeave', vi.fn());
    ConfigPage = (await import('./config.vue')).default;
  });

  beforeEach(() => {
    isMobile.value = true;
    isMobileOrTablet.value = true;
    vi.mocked(useBreakpointQuery).mockReturnValue({
      isMobile,
      isMobileOrTablet,
    } as ReturnType<typeof useBreakpointQuery>);
    vi.mocked(useConfirm).mockReturnValue({
      confirm: vi.fn(),
    } as ReturnType<typeof useConfirm>);
    vi.mocked(useConfigStore).mockReturnValue(
      configStore as unknown as ReturnType<typeof useConfigStore>
    );
  });

  afterEach(() => {
    delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView;
  });

  it('should expose settings search on mobile', () => {
    const wrapper = mountConfig();

    expect(wrapper.find('.config-mobile-search').exists()).toBe(true);
  });

  it('should expose every settings section in mobile navigation', () => {
    const wrapper = mountConfig();

    expect(wrapper.findAll('.config-mobile-section option')).toHaveLength(14);
  });

  it('should preserve the existing tablet layout without mobile tools', () => {
    isMobile.value = false;
    const wrapper = mountConfig();

    expect(wrapper.find('.config-mobile-tools').exists()).toBe(false);
  });

  it('should scroll to the first visible section when search hides the active section', async () => {
    const scrolledElements: HTMLElement[] = [];
    const scrollIntoView = vi.fn(function (this: HTMLElement) {
      scrolledElements.push(this);
    });
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    });
    const wrapper = mountConfig();

    await wrapper.get('.config-mobile-search').setValue('api');
    await nextTick();

    expect(scrolledElements[0] === wrapper.get('.config-section').element).toBe(
      true
    );
  });

  it('should sync the first visible section when entering mobile after desktop search', async () => {
    const scrolledElements: HTMLElement[] = [];
    const scrollIntoView = vi.fn(function (this: HTMLElement) {
      scrolledElements.push(this);
    });
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    });
    isMobile.value = false;
    isMobileOrTablet.value = false;
    const wrapper = mountConfig();

    await wrapper.get('.rail-search').setValue('api');
    isMobile.value = true;
    isMobileOrTablet.value = true;
    await nextTick();

    expect(scrolledElements[0] === wrapper.get('.config-section').element).toBe(
      true
    );
  });
});
