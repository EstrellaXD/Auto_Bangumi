import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { apiDownloader } from '@/api/downloader';
import { useDownloaderStore } from '@/store/downloader';
import type { QbTorrentInfo } from '#/downloader';

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

function torrent(hash: string, downloaderId: string) {
  return { hash, downloader_id: downloaderId } as QbTorrentInfo;
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
    store.selectedHashes = ['a1', 'b1', 'a2'];

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
});
