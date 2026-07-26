/* eslint-disable vue/one-component-per-file */
import { mount } from '@vue/test-utils';
import { computed, defineComponent, ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AbTorrentListPage from '../ab-torrent-list-page.vue';
import type { Torrent } from '#/torrent';

const isMobile = ref(true);
const torrents = ref<Torrent[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const toggleAll = vi.fn();

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile }),
}));

vi.mock('@/hooks/useTorrentList', () => ({
  useTorrentList: () => ({
    torrents,
    selectedIds,
    load: vi.fn(),
    allSelected: computed(
      () =>
        torrents.value.length > 0 &&
        selectedIds.value.size === torrents.value.length
    ),
    toggleAll,
    toggleOne: vi.fn(),
    runDelete: vi.fn(),
  }),
}));

vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

const ButtonStub = defineComponent({
  emits: ['click'],
  template:
    '<button @click="$emit(\'click\', $event)"><slot name="icon" /><slot /></button>',
});

const MenuStub = defineComponent({
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
  template: `
    <div class="menu-stub">
      <slot name="trigger" />
      <span v-for="item in items" :key="item.key">
        {{ typeof item.label === 'function' ? item.label() : item.label }}
      </span>
    </div>
  `,
});

describe('ab-torrent-list-page mobile actions', () => {
  beforeEach(() => {
    vi.stubGlobal('useI18n', () => ({ t: (key: string) => key }));
    isMobile.value = true;
    torrents.value = [
      {
        id: 1,
        name: 'Episode 01',
        downloaded: true,
        rss_id: 1,
      } as Torrent,
      {
        id: 2,
        name: 'Episode 02',
        downloaded: false,
        rss_id: null,
      } as Torrent,
    ];
    selectedIds.value = new Set([1]);
    toggleAll.mockClear();
  });

  function mountPage() {
    return mount(AbTorrentListPage, {
      props: {
        title: 'Torrents',
        loadFn: vi.fn(),
        deleteOne: vi.fn(),
        deleteAll: vi.fn(),
      },
      global: {
        stubs: {
          'ab-button': ButtonStub,
          'ab-icon-button': ButtonStub,
          'ab-menu': MenuStub,
          'ab-tag': true,
          'ab-empty': true,
        },
      },
    });
  }

  it('should move mobile selection actions into a bottom toolbar', () => {
    const wrapper = mountPage();

    expect(wrapper.get('.torrent-selection-toolbar').text()).toContain(
      'homepage.torrents.delete_selected'
    );
  });

  it('should keep clear all reachable from the mobile overflow menu', () => {
    const wrapper = mountPage();

    expect(wrapper.get('.torrent-mobile-menu').text()).toContain(
      'homepage.torrents.deleteAll'
    );
  });
});
