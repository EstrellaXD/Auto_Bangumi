import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import type { Component } from 'vue';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfigStore } from '@/store/config';
import { useDownloaderStore } from '@/store/downloader';
import { mockConfig } from '@/test/mocks/api';
import type { Config } from '#/config';
import type { QbTorrentInfo } from '#/downloader';

// happy-dom 没有布局：给虚拟列表一个固定视口高度，否则一行都不渲染。
// 必须在 naive-ui（vueuc 的 ResizeObserver 单例）加载前替换
vi.hoisted(() => {
  class FixedResizeObserver {
    callback: ResizeObserverCallback;
    constructor(callback: ResizeObserverCallback) {
      this.callback = callback;
    }

    observe(target: Element) {
      const entry = { target, contentRect: { width: 1000, height: 600 } };
      this.callback(
        [entry as unknown as ResizeObserverEntry],
        this as unknown as ResizeObserver
      );
    }

    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = FixedResizeObserver;
});

const downloaderData = ref<QbTorrentInfo[] | null>(null);

vi.mock('@/hooks/useEventStream', () => ({
  useEventStream: () => ({ connected: ref(true), downloaderData }),
}));

vi.mock('@/utils/axios', () => ({
  axios: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('@/api/downloader', () => ({
  apiDownloader: {
    getTorrents: vi.fn().mockResolvedValue([]),
    instances: vi.fn().mockResolvedValue({ default: '', instances: [] }),
  },
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string) => key,
    returnUserLangMsg: () => '',
  }),
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn() }),
}));

function torrent(
  hash: string,
  savePath: string,
  progress = 0.5
): QbTorrentInfo {
  return {
    hash,
    name: `torrent-${hash}`,
    size: 1024,
    progress,
    dlspeed: 0,
    upspeed: 0,
    num_seeds: 0,
    num_leechs: 0,
    state: 'downloading',
    eta: 0,
    category: 'Bangumi',
    save_path: savePath,
    added_on: 0,
    downloader_id: 'default',
  };
}

describe('Downloader page', () => {
  let DownloaderPage: Component;

  beforeAll(async () => {
    vi.stubGlobal('definePage', vi.fn());
    // vitest 的自动导入不含 @vueuse/core
    vi.stubGlobal('useIntervalFn', () => ({ pause: vi.fn(), resume: vi.fn() }));
    DownloaderPage = (await import('./downloader.vue')).default;
  });

  beforeEach(() => {
    setActivePinia(createPinia());
    useConfigStore().config = mockConfig as unknown as Config;
    downloaderData.value = null;
  });

  async function mountPage() {
    const wrapper = mount(DownloaderPage, {
      attachTo: document.body,
      global: { stubs: { 'ab-button': true, RouterLink: true } },
    });
    // 首帧在挂载后到达，与真实 SSE 一致（store 的 watch 不是 immediate）
    downloaderData.value = [
      torrent('a1', '/dl/Show A'),
      torrent('a2', '/dl/Show A'),
      torrent('b1', '/dl/Show B'),
    ];
    await flushPromises();
    return wrapper;
  }

  function rowOf(wrapper: Awaited<ReturnType<typeof mountPage>>, text: string) {
    const row = wrapper
      .findAll('.n-data-table-tbody .n-data-table-tr')
      .find((r) => r.text().includes(text));
    if (!row) throw new Error(`row not found: ${text}`);
    return row;
  }

  it('should update the row when the store receives a new SSE payload', async () => {
    const wrapper = await mountPage();
    expect(rowOf(wrapper, 'torrent-a1').text()).toContain('50%');

    downloaderData.value = [torrent('a1', '/dl/Show A', 1)];
    await flushPromises();

    expect(rowOf(wrapper, 'torrent-a1').text()).toContain('100%');
  });

  it('should select every torrent of the group when its header checkbox is checked', async () => {
    const wrapper = await mountPage();

    await rowOf(wrapper, 'Show A (2)').find('.n-checkbox').trigger('click');

    expect([...useDownloaderStore().selectedKeys].sort()).toEqual([
      'default:a1',
      'default:a2',
    ]);
    expect(wrapper.find('.action-bar-count').text()).toContain('2');
  });

  it('should hide the group rows when the group is collapsed', async () => {
    const wrapper = await mountPage();

    await rowOf(wrapper, 'Show A (2)')
      .find('.n-data-table-expand-trigger')
      .trigger('click');

    const text = wrapper.find('.n-data-table-tbody').text();
    expect(text).not.toContain('torrent-a1');
    expect(text).toContain('torrent-b1');
  });
});
