import { defineComponent, ref } from 'vue';
import type { Component } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppInfo } from '@/hooks/useAppInfo';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useBangumiStore } from '@/store/bangumi';
import { useDownloaderStore } from '@/store/downloader';
import { useRSSStore } from '@/store/rss';
import { mockBangumiRule } from '@/test/mocks/api';

vi.mock('@/hooks/useAppInfo', () => ({ useAppInfo: vi.fn() }));
vi.mock('@/hooks/useMyI18n', () => ({ useMyI18n: vi.fn() }));
vi.mock('@/store/bangumi', () => ({ useBangumiStore: vi.fn() }));
vi.mock('@/store/downloader', () => ({ useDownloaderStore: vi.fn() }));
vi.mock('@/store/rss', () => ({ useRSSStore: vi.fn() }));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: String, required: true } },
  template: '<a :href="to"><slot /></a>',
});

const actions = {
  getBangumi: vi.fn(),
  getDownloads: vi.fn(),
  getRss: vi.fn(),
};

let HomePage: Component;

function configureStores(rssUnavailable = false, pending = false) {
  vi.mocked(useBangumiStore).mockReturnValue({
    bangumi: [
      { ...mockBangumiRule, id: 1 },
      { ...mockBangumiRule, id: 2, needs_review: true },
    ],
    hasLoaded: !pending,
    loadFailed: false,
    isLoading: pending,
    getAll: actions.getBangumi,
  } as unknown as ReturnType<typeof useBangumiStore>);
  vi.mocked(useRSSStore).mockReturnValue({
    rss: [
      {
        id: 1,
        name: 'Mikan',
        url: 'https://mikan.example/rss',
        aggregate: false,
        parser: 'mikan',
        enabled: true,
        connection_status: 'error',
        last_checked_at: null,
        last_error: 'offline',
      },
    ],
    hasLoaded: !rssUnavailable && !pending,
    loadFailed: rssUnavailable,
    isLoading: pending,
    getAll: actions.getRss,
  } as unknown as ReturnType<typeof useRSSStore>);
  vi.mocked(useDownloaderStore).mockReturnValue({
    torrents: [],
    hasLoaded: !pending,
    loadFailed: false,
    loading: pending,
    getAll: actions.getDownloads,
  } as unknown as ReturnType<typeof useDownloaderStore>);
}

function mountHome(rssUnavailable = false, pending = false) {
  configureStores(rssUnavailable, pending);
  return mount(HomePage, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        'ab-status': true,
        'ab-tag': true,
      },
    },
  });
}

describe('mobile home page', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    HomePage = (await import('./home.vue')).default;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAppInfo).mockReturnValue({
      running: ref(true),
      statusKnown: ref(true),
      version: ref('3.3.4'),
    } as ReturnType<typeof useAppInfo>);
    vi.mocked(useMyI18n).mockReturnValue({
      t: (key: string) => key,
    } as ReturnType<typeof useMyI18n>);
  });

  it('should render the active rule count when Bangumi data is available', () => {
    const wrapper = mountHome();

    expect(
      wrapper.find('[data-summary="bangumi"] [data-value="primary"]').text()
    ).toBe('2');
  });

  it('should render the review count when a rule needs review', () => {
    const wrapper = mountHome();

    expect(
      wrapper.find('[data-summary="bangumi"] [data-value="secondary"]').text()
    ).toContain('1');
  });

  it('should render unavailable when an RSS first load fails', () => {
    const wrapper = mountHome(true);

    expect(wrapper.find('[data-summary="rss"]').text()).toContain(
      'mobile.unavailable'
    );
  });

  it('should render loading instead of zero before overview data arrives', () => {
    const wrapper = mountHome(false, true);

    expect(wrapper.find('[data-summary="bangumi"]').text()).toContain(
      'common.loading'
    );
  });

  it('should link the Bangumi summary to the full rule list', () => {
    const wrapper = mountHome();

    expect(wrapper.find('a[href="/bangumi"]').exists()).toBe(true);
  });

  it('should reload Bangumi when refresh is pressed', async () => {
    const wrapper = mountHome();
    await flushPromises();
    actions.getBangumi.mockClear();

    await wrapper.find('[data-action="refresh"]').trigger('click');

    expect(actions.getBangumi).toHaveBeenCalledTimes(1);
  });

  it('should reload RSS when refresh is pressed', async () => {
    const wrapper = mountHome();
    await flushPromises();
    actions.getRss.mockClear();

    await wrapper.find('[data-action="refresh"]').trigger('click');

    expect(actions.getRss).toHaveBeenCalledTimes(1);
  });

  it('should reload downloads when refresh is pressed', async () => {
    const wrapper = mountHome();
    await flushPromises();
    actions.getDownloads.mockClear();

    await wrapper.find('[data-action="refresh"]').trigger('click');

    expect(actions.getDownloads).toHaveBeenCalledTimes(1);
  });
});
