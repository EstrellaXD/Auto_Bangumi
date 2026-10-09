import { mount } from '@vue/test-utils';
import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import AbBangumiCard from '../ab-bangumi-card.vue';
import { mockBangumiRule } from '@/test/mocks/api';

vi.stubGlobal('resolvePosterUrl', (url: string) => url);

vi.mock('@/hooks/usePluginUi', () => ({
  useUiSlots: () =>
    ref([
      { plugin_id: 'demo', slot: 'bangumi.card.action', element: 'x-demo' },
    ]),
}));
vi.mock('../plugin-slot.vue', () => ({
  default: { template: '<button class="plugin-btn" />' },
}));

describe('ab-bangumi-card', () => {
  it('should render plugin actions outside the role=button card', () => {
    const w = mount(AbBangumiCard, {
      props: { bangumi: mockBangumiRule },
      global: { mocks: { $t: (k: string) => k }, stubs: { AbTag: true } },
    });

    expect(w.find('.plugin-btn').exists()).toBe(true);
    expect(w.find('[role="button"] .plugin-btn').exists()).toBe(false);
  });
});
