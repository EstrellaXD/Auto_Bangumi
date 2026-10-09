import { mount } from '@vue/test-utils';
import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import AbMobileNav from './ab-mobile-nav.vue';

vi.mock('@/hooks/useMyI18n', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  return { useMyI18n: () => ({ t: (k: string) => k, lang: ref('en') }) };
});
vi.stubGlobal('useRoute', () => ({ path: '/' }));
vi.mock('@/hooks/useDarkMode', async () => {
  const { ref } = await vi.importActual<typeof import('vue')>('vue');
  return { useDarkMode: () => ({ isDark: ref(false), toggle: vi.fn() }) };
});
vi.mock('vue-inline-svg', () => ({ default: { template: '<i />' } }));
vi.mock('@/hooks/usePluginUi', () => ({
  slotTitle: (ui: { title: Record<string, string> }) => ui.title['en-US'],
  useUiSlots: () =>
    ref([
      {
        plugin_id: 'demo',
        slot: 'page',
        element: 'x-demo',
        title: { 'en-US': 'Demo page' },
      },
    ]),
}));

describe('ab-mobile-nav', () => {
  it('should list plugin pages before the settings entry', () => {
    const w = mount(AbMobileNav, {
      global: {
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="to"><slot /></a>',
          },
        },
      },
    });

    const hrefs = w.findAll('a').map((a) => a.attributes('href'));
    expect(hrefs).toContain('/plugins/demo');
    expect(hrefs.indexOf('/plugins/demo')).toBe(hrefs.indexOf('/config') - 1);
  });
});
