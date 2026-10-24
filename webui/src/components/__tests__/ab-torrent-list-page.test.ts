import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import AbTorrentListPage from '../ab-torrent-list-page.vue';

vi.mock('@/hooks/useDownloaderInstances', () => ({
  useDownloaderInstances: () => ({ multiple: ref(true) }),
}));
vi.mock('@/hooks/useTorrentList', () => ({
  useTorrentList: () => ({
    torrents: ref([
      {
        id: 1,
        name: 'ep01',
        downloaded: true,
        downloader_id: 'qb-2',
        rss_id: 1,
      },
    ]),
    selectedIds: ref(new Set()),
    load: vi.fn(),
    allSelected: ref(false),
    toggleAll: vi.fn(),
    toggleOne: vi.fn(),
    runDelete: vi.fn(),
  }),
}));
vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn() }),
}));

vi.stubGlobal('useI18n', () => ({ t: (key: string) => key }));

describe('ab-torrent-list-page', () => {
  it('should label the downloader tag when several downloaders exist', async () => {
    const wrapper = mount(AbTorrentListPage, {
      props: {
        title: 'Torrents',
        loadFn: async () => [],
        deleteOne: async () => undefined,
        deleteAll: async () => undefined,
      },
      global: {
        mocks: {
          $t: (key: string, params?: Record<string, string>) =>
            params ? `${key}|${params.id}` : key,
        },
        stubs: {
          'ab-tag': { props: ['title'], template: '<i>{{ title }}</i>' },
        },
      },
    });
    await flushPromises();
    expect(wrapper.text()).toContain('homepage.torrents.downloader_tag|qb-2');
  });
});
