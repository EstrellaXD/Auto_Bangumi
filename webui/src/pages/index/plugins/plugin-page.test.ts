import { flushPromises, mount } from '@vue/test-utils';
import { ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import PluginPage from './[id].vue';

vi.stubGlobal('definePage', vi.fn());
vi.stubGlobal('useRoute', () => ({ params: { id: 'demo' } }));

const state = {
  slots: ref([]),
  loaded: ref(false),
  loadFailed: ref(false),
};
const refreshPluginUi = vi.fn();

vi.mock('@/hooks/usePluginUi', () => ({
  usePluginUi: () => state,
  refreshPluginUi: () => refreshPluginUi(),
}));
vi.mock('@/components/plugin-slot.vue', () => ({
  default: { template: '<div class="slot-stub" />' },
}));

const AbEmpty = {
  props: ['title'],
  template: '<div class="empty">{{ title }}<slot name="action" /></div>',
};
const AbButton = { template: '<button><slot /></button>' };
const AbSkeleton = { template: '<div class="skeleton" />' };

function mountPage() {
  return mount(PluginPage, {
    global: {
      components: { AbEmpty, AbButton, AbSkeleton },
      mocks: { $t: (k: string) => k },
    },
  });
}

describe('plugin page', () => {
  it('should show a skeleton while the slot list is loading', () => {
    const w = mountPage();
    expect(w.find('.skeleton').exists()).toBe(true);
  });

  it('should show a retry action when the slot list failed to load', async () => {
    state.loadFailed.value = true;
    const w = mountPage();
    expect(w.find('.skeleton').exists()).toBe(false);
    expect(w.find('.empty').text()).toContain('plugin.load_failed_page');

    await w.find('button').trigger('click');
    await flushPromises();
    expect(refreshPluginUi).toHaveBeenCalledTimes(1);
  });
});
