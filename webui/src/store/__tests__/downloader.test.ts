import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { apiDownloader } from '@/api/downloader';
import {
  hasConfiguredDownloader,
  torrentKey,
  useDownloaderStore,
} from '@/store/downloader';
import type { QbTorrentInfo } from '#/downloader';
import type { PluginInstance } from '#/config';

vi.mock('@/api/downloader', () => ({
  apiDownloader: {
    getTorrents: vi.fn().mockResolvedValue([]),
    pause: vi.fn().mockResolvedValue({}),
    resume: vi.fn().mockResolvedValue({}),
    deleteTorrents: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('@/hooks/useEventStream', () => ({
  useEventStream: () => ({ downloaderData: ref(null) }),
}));

vi.mock('@/hooks/useApi', () => ({
  useApi: (api: (...args: unknown[]) => Promise<unknown>) => ({
    execute: (...args: unknown[]) => api(...args),
  }),
}));

const errorMock = vi.fn();
vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: errorMock }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    returnUserLangMsg: (res: { msg_en: string }) => res.msg_en,
  }),
}));

function torrent(hash: string, downloaderId: string) {
  return { hash, downloader_id: downloaderId } as QbTorrentInfo;
}

function instance(options: Record<string, unknown>): PluginInstance {
  return { id: 'x', point: 'downloader', provider: 'p', options };
}

describe('downloader store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should send one request per downloader instance for the selected torrents', async () => {
    const store = useDownloaderStore();
    store.torrents = [
      torrent('a1', 'default'),
      torrent('b1', 'nas'),
      torrent('a2', 'default'),
      torrent('a3', 'default'),
    ];
    store.selectedKeys = store.torrents.slice(0, 3).map(torrentKey);

    await store.pauseSelected();
    await store.deleteSelected(true);

    expect(vi.mocked(apiDownloader.pause).mock.calls).toEqual([
      [['a1', 'a2'], 'default'],
      [['b1'], 'nas'],
    ]);
    expect(vi.mocked(apiDownloader.deleteTorrents).mock.calls).toEqual([
      [['a1', 'a2'], 'default', true],
      [['b1'], 'nas', true],
    ]);
  });

  it('should act only on the selected instance when the same hash is in two instances', async () => {
    const store = useDownloaderStore();
    store.torrents = [torrent('h', 'home'), torrent('h', 'seedbox')];
    store.selectedKeys = [torrentKey(store.torrents[1])];

    await store.pauseSelected();

    expect(vi.mocked(apiDownloader.pause).mock.calls).toEqual([
      [['h'], 'seedbox'],
    ]);
  });

  it.each([
    ['throws', () => Promise.reject(new Error('offline'))],
    [
      'returns status false',
      () =>
        Promise.resolve({ status: false, msg_en: 'Failed', msg_zh: '失败' }),
    ],
  ])(
    'should still run the other instances and fail when one instance %s',
    async (_, failure) => {
      const store = useDownloaderStore();
      store.torrents = [torrent('a', 'home'), torrent('b', 'seedbox')];
      store.selectedKeys = store.torrents.map(torrentKey);
      vi.mocked(apiDownloader.deleteTorrents).mockImplementationOnce(failure);

      await expect(store.deleteSelected(false)).rejects.toBeTruthy();

      expect(vi.mocked(apiDownloader.deleteTorrents).mock.calls).toEqual([
        [['a'], 'home', false],
        [['b'], 'seedbox', false],
      ]);
    }
  );

  it('should show the failure message when an instance returns status false', async () => {
    const store = useDownloaderStore();
    store.torrents = [torrent('a', 'home')];
    store.selectedKeys = store.torrents.map(torrentKey);
    vi.mocked(apiDownloader.deleteTorrents).mockResolvedValueOnce({
      status: false,
      msg_en: 'Failed to delete torrents',
      msg_zh: '删除种子失败',
    });

    await expect(store.deleteSelected(false)).rejects.toBeTruthy();

    expect(errorMock).toHaveBeenCalledTimes(1);
  });
});

describe('hasConfiguredDownloader', () => {
  it.each([
    [[], false],
    [[instance({ host: '' })], false],
    [[instance({ host: '' }), instance({ host: 'seedbox:8080' })], true],
    [[instance({ token: 'x' })], true],
  ] as [PluginInstance[], boolean][])(
    'should return the expected value when instances are %j',
    (instances, expected) => {
      expect(hasConfiguredDownloader(instances)).toBe(expected);
    }
  );
});
