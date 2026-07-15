import { createPinia, setActivePinia } from 'pinia';
import { nextTick, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDownloaderStore } from '../downloader';
import { useRSSStore } from '../rss';
import { apiDownloader } from '@/api/downloader';
import { apiRSS } from '@/api/rss';

vi.mock('@/api/downloader', () => ({
  apiDownloader: {
    getTorrents: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    deleteTorrents: vi.fn(),
  },
}));

vi.mock('@/api/rss', () => ({
  apiRSS: {
    get: vi.fn(),
    update: vi.fn(),
    disableMany: vi.fn(),
    deleteMany: vi.fn(),
    enableMany: vi.fn(),
    refresh: vi.fn(),
    refreshAll: vi.fn(),
  },
}));

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({ execute: vi.fn(), isLoading: ref(false) }),
}));

const downloaderData = ref<unknown[] | null>(null);

vi.mock('@/hooks/useEventStream', () => ({
  useEventStream: () => ({ downloaderData }),
}));

describe('overview store loading state', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    downloaderData.value = null;
  });

  it('should mark RSS loaded when the request succeeds', async () => {
    vi.mocked(apiRSS.get).mockResolvedValue([]);
    const store = useRSSStore();

    await store.getAll();

    expect(store.hasLoaded).toBe(true);
  });

  it('should mark RSS unavailable when the request fails', async () => {
    vi.mocked(apiRSS.get).mockRejectedValue(new Error('offline'));
    const store = useRSSStore();

    await store.getAll();

    expect(store.loadFailed).toBe(true);
  });

  it('should mark downloads loaded when the request succeeds', async () => {
    vi.mocked(apiDownloader.getTorrents).mockResolvedValue([]);
    const store = useDownloaderStore();

    await store.getAll();

    expect(store.hasLoaded).toBe(true);
  });

  it('should mark downloads unavailable when the request fails', async () => {
    vi.mocked(apiDownloader.getTorrents).mockRejectedValue(
      new Error('offline')
    );
    const store = useDownloaderStore();

    await store.getAll();

    expect(store.loadFailed).toBe(true);
  });

  it('should mark downloads loaded when valid stream data arrives', async () => {
    const store = useDownloaderStore();

    downloaderData.value = [];
    await nextTick();

    expect(store.hasLoaded).toBe(true);
  });
});
