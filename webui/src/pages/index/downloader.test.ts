import { createPinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import type { Component } from 'vue';
import { shallowMount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfigStore } from '@/store/config';
import { useDownloaderStore } from '@/store/downloader';
import { initConfig } from '#/config';
import type { QbTorrentInfo } from '#/downloader';

const isMobile = ref(true);

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile }),
}));
vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn() }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/hooks/useEventStream', async () => {
  const { ref: vueRef } = await vi.importActual<typeof import('vue')>('vue');
  return {
    useEventStream: () => ({
      connected: vueRef(false),
      downloaderData: vueRef(null),
    }),
  };
});
vi.mock('@/utils/axios', () => ({
  axios: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const torrent: QbTorrentInfo = {
  hash: 'hash-1',
  name: 'Episode 1',
  size: 1024,
  progress: 0.5,
  dlspeed: 0,
  upspeed: 0,
  num_seeds: 1,
  num_leechs: 0,
  state: 'downloading',
  eta: 60,
  category: 'Bangumi',
  save_path: '/downloads/Show/Season 1',
  added_on: 1,
};

let DownloaderPage: Component;

function mountPage() {
  return shallowMount(DownloaderPage, {
    global: {
      stubs: {
        AbDownloaderMobileList: {
          template: '<div data-testid="mobile-downloader-list" />',
        },
        AbFoldPanel: { template: '<section><slot /></section>' },
        AbButton: true,
        AbProgress: true,
        AbTag: true,
        NDataTable: true,
        RouterLink: true,
      },
    },
  });
}

describe('downloader responsive surface', () => {
  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    vi.stubGlobal('useIntervalFn', () => ({
      pause: vi.fn(),
      resume: vi.fn(),
    }));
    DownloaderPage = (await import('./downloader.vue')).default;
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    isMobile.value = true;

    const configStore = useConfigStore();
    configStore.config = structuredClone(initConfig);
    configStore.config.downloader.host = 'http://qbittorrent:8080';
    vi.spyOn(configStore, 'getConfig').mockResolvedValue();

    const downloaderStore = useDownloaderStore();
    downloaderStore.torrents = [torrent];
    vi.spyOn(downloaderStore, 'getAll').mockResolvedValue();
  });

  it('should render the compact torrent list on phones', () => {
    const wrapper = mountPage();

    expect(
      wrapper.find('[data-testid="mobile-downloader-list"]').exists()
    ).toBe(true);
  });

  it('should preserve grouped tables at the 640px boundary and above', () => {
    isMobile.value = false;
    const wrapper = mountPage();

    expect(wrapper.find('.downloader-groups').exists()).toBe(true);
  });
});
