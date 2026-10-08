import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';
import { apiConfig } from '@/api/config';
import { useConfigStore } from '@/store/config';
import { type Config, initConfig } from '#/config';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

vi.mock('@/hooks/useApi', () => ({
  useApi: () => ({ execute: vi.fn() }),
}));

vi.mock('@/api/config', () => ({
  apiConfig: { getConfig: vi.fn(), updateConfig: vi.fn() },
}));

function clone(config: Config): Config {
  return JSON.parse(JSON.stringify(config));
}

describe('config store refreshGroup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('replaces one group in both the draft and the snapshot, keeping other edits', async () => {
    const server = clone(initConfig);
    vi.mocked(apiConfig.getConfig).mockResolvedValue(clone(server));
    const store = useConfigStore();
    await store.getConfig();

    // 用户改了别的段（未保存），同时插件卡片直接保存了 plugins 段
    store.config.program.rss_time = 1234;
    server.plugins.enabled = { demo: true };
    vi.mocked(apiConfig.getConfig).mockResolvedValue(clone(server));
    await store.refreshGroup('plugins');

    expect(store.config.plugins.enabled).toEqual({ demo: true });
    expect(store.config.program.rss_time).toBe(1234);
    // plugins 段不再算作未保存，program 段仍然是脏的
    expect(store.dirtyGroups).toContain('program');
    expect(store.dirtyGroups).not.toContain('plugins');
  });
});
