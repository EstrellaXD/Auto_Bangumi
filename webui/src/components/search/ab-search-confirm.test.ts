/* eslint-disable vue/one-component-per-file */

import { flushPromises, mount } from '@vue/test-utils';
import { defineComponent, nextTick } from 'vue';
import AbSearchConfirm from './ab-search-confirm.vue';
import BangumiRssLinkRow from '@/components/bangumi-rss-link-row.vue';
import BangumiRssPreviewDialog from '@/components/bangumi-rss-preview-dialog.vue';
import { apiBangumi } from '@/api/bangumi';
import { apiRSS } from '@/api/rss';
import { mockBangumiRule } from '@/test/mocks/api';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/api/rss', () => ({
  apiRSS: {
    preview: vi.fn(),
  },
}));

vi.mock('@/api/bangumi', () => ({
  apiBangumi: {
    detectOffset: vi.fn(),
    suggestOffset: vi.fn(),
  },
}));

const previewMock = vi.mocked(apiRSS.preview);
const detectOffsetMock = vi.mocked(apiBangumi.detectOffset);

vi.mock('naive-ui', async () => {
  const actual = await vi.importActual<typeof import('naive-ui')>('naive-ui');
  return {
    ...actual,
    NDynamicTags: defineComponent({
      name: 'NDynamicTagsStub',
      props: {
        value: {
          type: Array,
          default: () => [],
        },
      },
      emits: ['update:value'],
      template: '<div class="dynamic-tags-stub"></div>',
    }),
    NSpin: defineComponent({
      name: 'NSpinStub',
      template: '<div class="n-spin-stub"></div>',
    }),
    NTooltip: defineComponent({
      name: 'NTooltipStub',
      template:
        '<div class="n-tooltip-stub"><slot name="trigger" /><slot /></div>',
    }),
    NDataTable: defineComponent({
      name: 'NDataTableStub',
      props: {
        data: {
          type: Array,
          default: () => [],
        },
      },
      template: `
        <div class="n-data-table-stub">
          <div
            v-for="item in data"
            :key="item.url + item.name"
            class="rss-preview-table-row"
          >
            <span class="rss-preview-table-name">{{ item.name }}</span>
            <span
              :class="
                item.passesFilter
                  ? 'rss-preview-status rss-preview-status--passed'
                  : 'rss-preview-status rss-preview-status--blocked'
              "
            ></span>
          </div>
        </div>
      `,
    }),
    useMessage: () => ({
      error: vi.fn(),
    }),
  };
});

const IconButtonStub = defineComponent({
  name: 'AbIconButtonStub',
  props: {
    label: {
      type: String,
      default: '',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  template: '<button type="button" :disabled="disabled"><slot /></button>',
});

const ButtonStub = defineComponent({
  name: 'AbButtonStub',
  props: {
    variant: {
      type: String,
      default: 'default',
    },
  },
  template: '<button type="button"><slot /></button>',
});

const InputStub = defineComponent({
  name: 'AbInputStub',
  props: {
    modelValue: {
      type: [String, Number],
      default: '',
    },
    value: {
      type: [String, Number],
      default: '',
    },
    type: {
      type: String,
      default: 'text',
    },
  },
  emits: ['update:modelValue'],
  template: '<input />',
});

const ModalStub = defineComponent({
  name: 'AbModalStub',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
  },
  template: '<div v-if="show" class="ab-modal-stub"><slot /></div>',
});

const TagStub = defineComponent({
  name: 'AbTagStub',
  props: {
    title: {
      type: String,
      default: '',
    },
  },
  template: '<span class="ab-tag-stub">{{ title }}</span>',
});

const EmptyStub = defineComponent({
  name: 'AbEmptyStub',
  props: {
    title: {
      type: String,
      default: '',
    },
  },
  template: '<div class="ab-empty-stub">{{ title }}</div>',
});

function mountComponent() {
  return mount(AbSearchConfirm, {
    props: {
      bangumi: { ...mockBangumiRule },
    },
    global: {
      components: {
        'bangumi-rss-link-row': BangumiRssLinkRow,
        'bangumi-rss-preview-dialog': BangumiRssPreviewDialog,
      },
      stubs: {
        'ab-icon-button': IconButtonStub,
        'ab-button': ButtonStub,
        'ab-input': InputStub,
        'ab-modal': ModalStub,
        'ab-tag': TagStub,
        'ab-empty': EmptyStub,
        'ab-offset-mismatch-dialog': true,
      },
    },
  });
}

describe('ab-search-confirm', () => {
  beforeEach(() => {
    previewMock.mockReset();
    detectOffsetMock.mockReset();
    detectOffsetMock.mockResolvedValue({
      has_mismatch: false,
      suggestion: null,
      tmdb_info: null,
    });
  });

  it('loads RSS preview rows when expanded', async () => {
    previewMock.mockResolvedValue({
      items: [
        {
          name: '[TestGroup] Test Anime - 01 [1080p].mkv',
          url: 'https://example.com/1.torrent',
          homepage: null,
        },
        {
          name: '[TestGroup] Test Anime - 01 [720p].mkv',
          url: 'https://example.com/2.torrent',
          homepage: null,
        },
      ],
      global_filter: [],
    });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.find('.preview-btn').trigger('click');
    await flushPromises();

    expect(previewMock).toHaveBeenCalledWith(mockBangumiRule.rss_link[0]);
    expect(wrapper.findAll('.rss-preview-table-row')).toHaveLength(2);
    expect(wrapper.find('.rss-preview-status--passed').exists()).toBe(true);
    expect(wrapper.find('.rss-preview-status--blocked').exists()).toBe(true);
  });

  it('recomputes preview status locally when filter rules change', async () => {
    previewMock.mockResolvedValue({
      items: [
        {
          name: '[TestGroup] Test Anime - 01 [720p].mkv',
          url: 'https://example.com/old.torrent',
          homepage: null,
        },
        {
          name: '[TestGroup] Test Anime - 01 [1080p].mkv',
          url: 'https://example.com/new.torrent',
          homepage: null,
        },
      ],
      global_filter: [],
    });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.find('.preview-btn').trigger('click');
    await flushPromises();
    let items = wrapper.findAll('.rss-preview-table-row');
    expect(items[0].text()).toContain('[TestGroup] Test Anime - 01 [720p].mkv');
    expect(items[0].find('.rss-preview-status--blocked').exists()).toBe(true);
    expect(items[1].find('.rss-preview-status--passed').exists()).toBe(true);

    const tags = wrapper.findComponent({ name: 'NDynamicTagsStub' });
    tags.vm.$emit('update:value', ['1080']);
    await nextTick();
    await flushPromises();

    expect(previewMock).toHaveBeenCalledTimes(1);
    items = wrapper.findAll('.rss-preview-table-row');
    expect(items[0].find('.rss-preview-status--passed').exists()).toBe(true);
    expect(items[1].find('.rss-preview-status--blocked').exists()).toBe(true);
  });

  it('applies API global filters when classifying preview rows', async () => {
    previewMock.mockResolvedValue({
      items: [
        {
          name: '[TestGroup] Test Anime - 01 [1080p].mkv',
          url: 'https://example.com/1.torrent',
          homepage: null,
        },
        {
          name: '[TestGroup] Test Anime - 01 [720p].mkv',
          url: 'https://example.com/2.torrent',
          homepage: null,
        },
      ],
      global_filter: ['1080'],
    });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.find('.preview-btn').trigger('click');
    await flushPromises();

    const items = wrapper.findAll('.rss-preview-table-row');
    expect(items[0].find('.rss-preview-status--blocked').exists()).toBe(true);
    expect(items[1].find('.rss-preview-status--blocked').exists()).toBe(true);
  });

  it('deduplicates preview filters in dialog', async () => {
    previewMock.mockResolvedValue({
      items: [],
      global_filter: ['720', '1080', '720'],
    });

    const wrapper = mount(AbSearchConfirm, {
      props: {
        bangumi: {
          ...mockBangumiRule,
          filter: ['1080', '720'],
        },
      },
      global: {
        components: {
          'bangumi-rss-link-row': BangumiRssLinkRow,
          'bangumi-rss-preview-dialog': BangumiRssPreviewDialog,
        },
        stubs: {
          'ab-icon-button': IconButtonStub,
          'ab-button': ButtonStub,
          'ab-input': InputStub,
          'ab-modal': ModalStub,
          'ab-tag': TagStub,
          'ab-empty': EmptyStub,
          'ab-offset-mismatch-dialog': true,
        },
      },
    });
    await flushPromises();

    await wrapper.find('.preview-btn').trigger('click');
    await flushPromises();

    const filters = wrapper
      .findAll('.rss-preview-filter-tag')
      .map((item) => item.text());
    expect(filters).toEqual(['720', '1080']);
  });
});
