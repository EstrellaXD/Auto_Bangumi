/* eslint-disable vue/one-component-per-file */
import { defineComponent, reactive, ref } from 'vue';
import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AbTopbar from '../ab-topbar.vue';
import { useAddRss } from '@/hooks/useAddRss';
import { useAppInfo } from '@/hooks/useAppInfo';
import { useBreakpointQuery } from '@/hooks/useBreakpointQuery';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useBangumiStore } from '@/store/bangumi';
import { useProgramStore } from '@/store/program';
import { useSearchStore } from '@/store/search';

const route = reactive({ path: '/' });

vi.mock('vue-router', () => ({ useRoute: () => route }));
vi.mock('@/hooks/useAddRss', () => ({ useAddRss: vi.fn() }));
vi.mock('@/hooks/useAppInfo', () => ({ useAppInfo: vi.fn() }));
vi.mock('@/hooks/useBreakpointQuery', () => ({ useBreakpointQuery: vi.fn() }));
vi.mock('@/hooks/useDarkMode', () => ({ useDarkMode: vi.fn() }));
vi.mock('@/hooks/useMyI18n', () => ({ useMyI18n: vi.fn() }));
vi.mock('@/store/bangumi', () => ({ useBangumiStore: vi.fn() }));
vi.mock('@/store/program', () => ({ useProgramStore: vi.fn() }));
vi.mock('@/store/search', () => ({ useSearchStore: vi.fn() }));

const SearchBarStub = defineComponent({
  name: 'AbSearchBar',
  template: '<div data-search-bar />',
});

const StatusBarStub = defineComponent({
  name: 'AbStatusBar',
  template: '<div data-status-bar />',
});

const StatusStub = defineComponent({
  name: 'AbStatus',
  props: { label: String },
  template: '<div data-mobile-status>{{ label }}</div>',
});

const isMobile = ref(true);
const running = ref(true);
const statusKnown = ref(true);

function mountTopbar() {
  return mount(AbTopbar, {
    global: {
      stubs: {
        AbAddRss: true,
        AbChangeAccount: true,
        AbNotificationCenter: true,
        AbSearchBar: SearchBarStub,
        AbStatus: StatusStub,
        AbStatusBar: StatusBarStub,
      },
    },
  });
}

describe('ab-topbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    route.path = '/';
    isMobile.value = true;
    running.value = true;
    statusKnown.value = true;
    vi.mocked(useAddRss).mockReturnValue({
      showAddRss: ref(false),
      openAddRss: vi.fn(),
      closeAddRss: vi.fn(),
    });
    vi.mocked(useAppInfo).mockReturnValue({
      running,
      statusKnown,
      version: ref('3.3.4'),
      onUpdate: vi.fn(),
      offUpdate: vi.fn(),
    });
    vi.mocked(useBreakpointQuery).mockReturnValue({
      isMobile,
    } as ReturnType<typeof useBreakpointQuery>);
    vi.mocked(useDarkMode).mockReturnValue({
      isDark: ref(false),
    } as unknown as ReturnType<typeof useDarkMode>);
    vi.mocked(useMyI18n).mockReturnValue({
      t: (key: string) => key,
      changeLocale: vi.fn(),
    } as unknown as ReturnType<typeof useMyI18n>);
    vi.mocked(useBangumiStore).mockReturnValue({
      refreshPoster: vi.fn(),
    } as unknown as ReturnType<typeof useBangumiStore>);
    vi.mocked(useProgramStore).mockReturnValue({
      pause: vi.fn(),
      resetRule: vi.fn(),
      restart: vi.fn(),
      shutdown: vi.fn(),
      start: vi.fn(),
    } as unknown as ReturnType<typeof useProgramStore>);
    vi.mocked(useSearchStore).mockReturnValue({
      toggleModal: vi.fn(),
    } as unknown as ReturnType<typeof useSearchStore>);
  });

  it('should not mount the modal search trigger on mobile', () => {
    const wrapper = mountTopbar();

    expect(wrapper.find('[data-search-bar]').exists()).toBe(false);
  });

  it('should not mount the system menu on mobile', () => {
    const wrapper = mountTopbar();

    expect(wrapper.find('[data-status-bar]').exists()).toBe(false);
  });

  it('should show an explicit running label on mobile', () => {
    const wrapper = mountTopbar();

    expect(wrapper.get('[data-mobile-status]').text()).toBe('mobile.running');
  });

  it('should show an unavailable label before program status is known', () => {
    statusKnown.value = false;

    const wrapper = mountTopbar();

    expect(wrapper.get('[data-mobile-status]').text()).toBe(
      'mobile.unavailable'
    );
  });

  it('should keep the modal search trigger on desktop routes', () => {
    isMobile.value = false;
    const wrapper = mountTopbar();

    expect(wrapper.find('[data-search-bar]').exists()).toBe(true);
  });

  it('should keep the system menu on desktop', () => {
    isMobile.value = false;
    const wrapper = mountTopbar();

    expect(wrapper.find('[data-status-bar]').exists()).toBe(true);
  });

  it('should not mount a second search surface on the search route', () => {
    isMobile.value = false;
    route.path = '/search';
    const wrapper = mountTopbar();

    expect(wrapper.find('[data-search-bar]').exists()).toBe(false);
  });
});
