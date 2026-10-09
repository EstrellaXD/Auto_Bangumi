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
  return { useMyI18n: () => ({ lang: ref('en') }) };
});

const slots = ref<unknown[]>([]);
vi.mock('@/hooks/usePluginUi', () => ({
  slotTitle: (ui: { title: Record<string, string> }) => ui.title['en-US'],
  usePluginUi: () => ({ slots }),
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
});
