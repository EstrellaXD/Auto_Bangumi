import { describe, expect, it, vi } from 'vitest';
import { createAbHost, resolveApiUrl } from '../plugin-host';
import type { HostDeps } from '../plugin-host';

function makeDeps(overrides: Partial<HostDeps> = {}): HostDeps {
  return {
    request: vi.fn().mockResolvedValue({ ok: true }),
    locale: () => 'zh-CN',
    t: (key) => key,
    isDark: () => false,
    tokens: () => ({ '--ab-color-text': '#000' }),
    toast: vi.fn(),
    onBusEvent: vi.fn(() => vi.fn()),
    ...overrides,
  };
}

describe('resolveApiUrl', () => {
  it.each([
    ['get', 'picks/3', 'api/v1/plugins/demo/picks/3'],
    ['post', 'backfill', 'api/v1/plugins/demo/backfill'],
    ['get', 'list?page=2', 'api/v1/plugins/demo/list?page=2'],
    // 自己前缀下的绝对路径：任何方法
    ['put', '/api/v1/plugins/demo/picks/3', 'api/v1/plugins/demo/picks/3'],
    // 宿主公开只读 API：仅 GET
    ['get', '/api/v1/bangumi/3/torrents', 'api/v1/bangumi/3/torrents'],
    // ../ 退出插件前缀但仍在 /api/v1/ 下：按公开只读 API 处理，只允许 GET
    ['get', '../other/x', 'api/v1/plugins/other/x'],
    // 相对路径中的 ../ 回到前缀内时仍然合法
    ['get', 'a/../b', 'api/v1/plugins/demo/b'],
  ] as const)('should resolve %s %s', (method, path, expected) => {
    expect(resolveApiUrl('demo', method, path)).toBe(expected);
  });

  it.each([
    ['post', '/api/v1/bangumi/3/torrents'],
    ['delete', '/api/v1/config/get'],
    ['post', '../other/x'],
    ['put', '%2e%2e/other/x'],
    ['get', '../../../../etc/x'],
    ['get', '/other/x'],
    ['get', '//evil.example/api/v1/x'],
    ['get', 'https://evil.example/api/v1/x'],
    // 另一个插件的路由只读可见，不可写
    ['post', '/api/v1/plugins/other/pick'],
  ] as const)('should reject %s %s', (method, path) => {
    expect(() => resolveApiUrl('demo', method, path)).toThrow(/may not/);
  });
});

describe('createAbHost', () => {
  it('should send scoped requests with params and body', async () => {
    const deps = makeDeps();
    const { host } = createAbHost('demo', deps);

    await host.api.get('picks/3', { page: 2 });
    await host.api.put('picks/3', { torrent_id: 9 });
    await host.api.delete('picks/3');

    expect(deps.request).toHaveBeenNthCalledWith(
      1,
      'get',
      'api/v1/plugins/demo/picks/3',
      { params: { page: 2 } }
    );
    expect(deps.request).toHaveBeenNthCalledWith(
      2,
      'put',
      'api/v1/plugins/demo/picks/3',
      { data: { torrent_id: 9 } }
    );
    expect(deps.request).toHaveBeenNthCalledWith(
      3,
      'delete',
      'api/v1/plugins/demo/picks/3',
      {}
    );
  });

  it('should reject without sending when the path leaves the scope', async () => {
    const deps = makeDeps();
    const { host } = createAbHost('demo', deps);

    await expect(host.api.post('/api/v1/config/update', {})).rejects.toThrow(
      /may not/
    );
    await expect(host.api.post('../other/x')).rejects.toThrow(/may not/);
    expect(deps.request).not.toHaveBeenCalled();
  });

  it('should read locale, theme and tokens live from the host', () => {
    let dark = false;
    let locale = 'zh-CN';
    const { host } = createAbHost(
      'demo',
      makeDeps({ isDark: () => dark, locale: () => locale })
    );

    expect(host.theme.mode).toBe('light');
    expect(host.i18n.locale).toBe('zh-CN');
    expect(host.theme.tokens).toEqual({ '--ab-color-text': '#000' });
    dark = true;
    locale = 'en-US';
    expect(host.theme.mode).toBe('dark');
    expect(host.i18n.locale).toBe('en-US');
  });

  it('should default the toast kind to info', () => {
    const deps = makeDeps();
    const { host } = createAbHost('demo', deps);

    host.toast('saved');
    host.toast('boom', 'error');

    expect(deps.toast).toHaveBeenNthCalledWith(1, 'saved', 'info');
    expect(deps.toast).toHaveBeenNthCalledWith(2, 'boom', 'error');
  });

  it('should unsubscribe every event listener on dispose', () => {
    const offs = [vi.fn(), vi.fn()];
    const deps = makeDeps({
      onBusEvent: vi
        .fn()
        .mockReturnValueOnce(offs[0])
        .mockReturnValueOnce(offs[1]),
    });
    const { host, dispose } = createAbHost('demo', deps);

    const unsubscribe = host.events.on('a', () => {});
    host.events.on('b', () => {});
    unsubscribe();
    expect(offs[0]).toHaveBeenCalledTimes(1);

    dispose();
    expect(offs[0]).toHaveBeenCalledTimes(1);
    expect(offs[1]).toHaveBeenCalledTimes(1);
  });
});
