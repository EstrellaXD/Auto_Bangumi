import { flushPromises, mount } from '@vue/test-utils';
import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MarketPage from './[[id]].vue';
import type { CatalogEntry } from '#/plugins';
import { apiPlugins } from '@/api/plugins';
import AbAlert from '@/components/basic/ab-alert.vue';
import AbButton from '@/components/basic/ab-button.vue';
import AbEmpty from '@/components/basic/ab-empty.vue';
import AbInput from '@/components/basic/ab-input.vue';
import AbSegmented from '@/components/basic/ab-segmented.vue';
import AbTag from '@/components/basic/ab-tag.vue';
import { refreshPluginProviders } from '@/hooks/usePluginProviders';
import { refreshPluginUi } from '@/hooks/usePluginUi';

vi.stubGlobal('definePage', vi.fn());
vi.stubGlobal('useRoute', () => ({ params: {} }));
vi.stubGlobal('useRouter', () => ({ back: vi.fn(), replace: vi.fn() }));
vi.stubGlobal('useIntervalFn', vi.fn());

vi.mock('@/api/plugins', () => ({
  apiPlugins: { catalog: vi.fn(), list: vi.fn(), install: vi.fn() },
}));
vi.mock('@/hooks/useMyI18n', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  return { useMyI18n: () => ({ t: (key: string) => key, lang: ref('en') }) };
});
vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ success: vi.fn(), error: vi.fn() }),
}));
vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile: ref(false) }),
}));
vi.mock('@/hooks/usePluginProviders', () => ({
  refreshPluginProviders: vi.fn(),
}));
vi.mock('@/hooks/usePluginUi', () => ({ refreshPluginUi: vi.fn() }));
const refreshGroup = vi.fn();
vi.mock('@/store/config', () => ({
  useConfigStore: () => ({ refreshGroup }),
}));

const api = vi.mocked(apiPlugins);
const getItem = vi.mocked(localStorage.getItem);
const setItem = vi.mocked(localStorage.setItem);

function entry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 'bili',
    name: 'Bilibili',
    version: '0.2.0',
    kind: 'plugin',
    extension_points: ['search_site'],
    description: '',
    sdk: '',
    min_ab_version: '4.0.0',
    authors: ['alice'],
    permissions: ['network'],
    has_web: false,
    repo: 'alice/bili',
    commit: '3f9c2e1aa',
    path: '.',
    readme: '',
    installed_version: null,
    ...overrides,
  };
}

async function mountPage() {
  const wrapper = mount(MarketPage, {
    global: {
      components: { AbAlert, AbButton, AbEmpty, AbInput, AbSegmented, AbTag },
      stubs: {
        AbSelect: true,
        AbSkeleton: true,
        AbIconButton: true,
        RouterLink: {
          props: ['to'],
          template: '<a class="row-link" :href="to"><slot /></a>',
        },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

function buttons(w: Awaited<ReturnType<typeof mountPage>>, text: string) {
  return w.findAll('button').filter((b) => b.text() === text);
}

describe('market page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getItem.mockReturnValue(null);
    api.list.mockResolvedValue({ allow_unsigned: false, plugins: [] });
  });

  it('should show the cached catalog with install disabled when the catalog is unavailable', async () => {
    getItem.mockReturnValue(
      JSON.stringify({ entries: [entry()], fetchedAt: 0 })
    );
    api.catalog.mockRejectedValue({
      status: 502,
      msg_en: '',
      msg_zh: '',
      detail: 'connect timeout',
    });

    const w = await mountPage();

    const alert = w.find('[role="alert"]');
    expect(alert.text()).toContain('market.stale_lead');
    expect(alert.text()).toContain('connect timeout');
    expect(w.findAll('.row-link')).toHaveLength(1);
    expect(
      buttons(w, 'market.install')[0].attributes('disabled')
    ).toBeDefined();
  });

  it('should keep the loaded catalog and disable install when a refresh fails', async () => {
    api.catalog.mockResolvedValueOnce([entry()]);
    const w = await mountPage();
    expect(w.find('[role="alert"]').exists()).toBe(false);

    api.catalog.mockRejectedValueOnce({ status: 0, msg_en: '', msg_zh: '' });
    await buttons(w, 'market.refresh')[0].trigger('click');
    await flushPromises();

    expect(w.find('[role="alert"]').text()).toContain('market.stale_lead');
    expect(getItem).not.toHaveBeenCalled();
    expect(w.findAll('.row-link')).toHaveLength(1);
    expect(
      buttons(w, 'market.install')[0].attributes('disabled')
    ).toBeDefined();
  });

  it('should show the error and recover on retry when there is no cache', async () => {
    api.catalog.mockRejectedValueOnce(new Error('down'));
    const w = await mountPage();
    expect(w.text()).toContain('market.load_failed');
    expect(w.find('.row-link').exists()).toBe(false);

    api.catalog.mockResolvedValue([entry()]);
    await buttons(w, 'market.retry')[0].trigger('click');
    await flushPromises();

    expect(w.text()).not.toContain('market.load_failed');
    expect(w.findAll('.row-link')).toHaveLength(1);
    expect(setItem).toHaveBeenCalled();
  });

  it('should offer to clear a search that matches nothing', async () => {
    api.catalog.mockResolvedValue([
      entry(),
      entry({ id: 'ntfy', name: 'ntfy' }),
    ]);
    const w = await mountPage();

    await w.find('input').setValue('jellyfin');
    expect(w.findAll('.row-link')).toHaveLength(0);
    expect(w.text()).toContain('market.no_match');

    await buttons(w, 'market.clear_search')[0].trigger('click');
    expect(w.findAll('.row-link')).toHaveLength(2);
  });

  it('should install after the confirm step and refresh catalog, config and plugin UI', async () => {
    api.catalog.mockResolvedValue([entry()]);
    api.install.mockResolvedValue({ allow_unsigned: false, plugins: [] });
    const w = await mountPage();

    await buttons(w, 'market.install')[0].trigger('click');
    expect(w.text()).toContain('market.warning');
    expect(api.install).not.toHaveBeenCalled();

    await buttons(w, 'market.install_enable')[0].trigger('click');
    await flushPromises();

    expect(api.install).toHaveBeenCalledWith('bili');
    expect(api.catalog).toHaveBeenCalledTimes(2);
    expect(refreshGroup).toHaveBeenCalledWith(
      'plugins',
      expect.arrayContaining(['enabled'])
    );
    expect(refreshPluginProviders).toHaveBeenCalled();
    expect(refreshPluginUi).toHaveBeenCalled();
    expect(w.text()).not.toContain('market.warning');
  });

  it('should stay on the confirm step when the install fails', async () => {
    api.catalog.mockResolvedValue([entry()]);
    api.install.mockRejectedValue(new Error('signature invalid'));
    const w = await mountPage();

    await buttons(w, 'market.install')[0].trigger('click');
    await buttons(w, 'market.install_enable')[0].trigger('click');
    await flushPromises();

    expect(w.text()).toContain('market.warning');
    expect(refreshPluginUi).not.toHaveBeenCalled();
  });
});
