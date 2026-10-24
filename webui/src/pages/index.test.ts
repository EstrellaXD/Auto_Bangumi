import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Index from './index.vue';

vi.stubGlobal('definePage', vi.fn());
vi.stubGlobal('useRoute', () => ({
  name: 'Plugin',
  params: { id: 'demo' },
}));
vi.mock('@/hooks/useMyI18n', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  return { useMyI18n: () => ({ t: (k: string) => k, lang: ref('en') }) };
});

const slots = ref<unknown[]>([]);
const loaded = ref(false);
const loadFailed = ref(false);
vi.mock('@/hooks/usePluginUi', () => ({
  slotTitle: (ui: { title: Record<string, string> }) => ui.title['en-US'],
  usePluginUi: () => ({ slots, loaded, loadFailed }),
}));
vi.mock('@/store/bangumi', () => ({
  useBangumiStore: () => ({ editRule: ref({}) }),
}));

const AbPageTitle = { props: ['title'], template: '<h1>{{ title }}</h1>' };

function mountIndex() {
  return mount(Index, {
    global: {
      components: { AbPageTitle },
      stubs: { RouterView: true, KeepAlive: true, transition: true },
    },
  });
}

describe('index page title', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    loaded.value = false;
    loadFailed.value = false;
  });

  it('should leave the title empty on a plugin route until the manifest arrives', async () => {
    slots.value = [];
    const w = mountIndex();
    expect(w.find('h1').text()).toBe('');

    slots.value = [
      { slot: 'page', plugin_id: 'demo', title: { 'en-US': 'Demo page' } },
    ];
    await w.vm.$nextTick();
    expect(w.find('h1').text()).toBe('Demo page');
  });

  // 插件已停用/不存在或清单加载失败时没有匹配的页面，标题回退为插件 id
  it.each([
    [true, false],
    [false, true],
  ])(
    'should fall back to the plugin id when loaded=%s failed=%s and no page matches',
    async (isLoaded, failed) => {
      slots.value = [];
      loaded.value = isLoaded;
      loadFailed.value = failed;
      const w = mountIndex();
      expect(w.find('h1').text()).toBe('demo');
    }
  );
});
