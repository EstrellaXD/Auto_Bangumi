import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { mount } from '@vue/test-utils';
import AbAddRss from '../ab-add-rss.vue';

vi.mock('@/hooks/useDownloaderInstances', () => ({
  useDownloaderInstances: () => ({
    multiple: ref(true),
    options: ref([{ label: 'qb', value: 'qb' }]),
    data: ref({ default: 'qb', instances: [] }),
  }),
}));
vi.mock('@/hooks/usePluginProviders', () => ({
  usePluginProviders: () => ref({ metadata_provider: [] }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/hooks/useApi', () => ({ useApi: () => ({ execute: vi.fn() }) }));
vi.mock('@/store/bangumi', () => ({
  useBangumiStore: () => ({ getAll: vi.fn() }),
}));
vi.mock('@/hooks/useBangumiRuleForm', () => ({
  useBangumiRuleForm: () => ({
    posterSrc: ref(''),
    infoTags: ref([]),
    showAdvanced: ref(false),
    copied: ref(false),
    copyRssLink: vi.fn(),
  }),
}));
vi.mock('@/utils/axios', () => ({ axios: {} }));
vi.mock('@/api/rss', () => ({ apiRSS: {} }));
vi.mock('@/api/download', () => ({ apiDownload: {} }));
vi.mock('naive-ui', async () => ({
  ...(await vi.importActual<object>('naive-ui')),
  useMessage: () => ({}),
}));

describe('ab-add-rss', () => {
  it('should give the downloader select an accessible name', () => {
    const wrapper = mount(AbAddRss, {
      props: { show: true },
      global: {
        mocks: { $t: (key: string) => key },
        stubs: { NSelect: { template: '<div class="n-select" />' } },
      },
    });
    const labels = wrapper
      .findAll('.n-select')
      .map((el) => el.attributes('aria-label'));
    expect(labels).toContain('topbar.add.downloader');
  });
});
