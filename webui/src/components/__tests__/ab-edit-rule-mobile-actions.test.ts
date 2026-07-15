/* eslint-disable vue/one-component-per-file */
import { readFileSync } from 'node:fs';
import { mount } from '@vue/test-utils';
import { defineComponent, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import AbEditRule from '../ab-edit-rule.vue';
import { mockBangumiRule } from '@/test/mocks/api';

vi.mock('naive-ui', async () => {
  const actual = await vi.importActual<typeof import('naive-ui')>('naive-ui');
  return {
    ...actual,
    useMessage: () => ({ success: vi.fn(), info: vi.fn(), error: vi.fn() }),
  };
});

vi.mock('@/utils/axios', () => ({
  axios: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile: ref(true) }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
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

const ModalStub = defineComponent({
  props: ['show'],
  template: '<div><slot /><footer><slot name="footer" /></footer></div>',
});

const MenuStub = defineComponent({
  props: {
    items: {
      type: Array,
      required: true,
    },
    placement: String,
  },
  template: `
    <div class="menu-stub" :data-placement="placement">
      <slot name="trigger" />
      <span v-for="item in items" :key="item.key" class="menu-label">
        {{ typeof item.label === 'function' ? item.label() : item.label }}
      </span>
    </div>
  `,
});

describe('ab-edit-rule mobile actions', () => {
  it('should keep secondary rule actions in a local mobile disclosure', () => {
    vi.stubGlobal('useRouter', () => ({ push: vi.fn() }));

    const wrapper = mount(AbEditRule, {
      props: {
        show: true,
        rule: { ...mockBangumiRule },
      },
      global: {
        stubs: {
          'ab-modal': ModalStub,
          'ab-menu': MenuStub,
          'ab-icon-button': { template: '<button><slot /></button>' },
          'ab-button': { template: '<button><slot /></button>' },
          'bangumi-preview': true,
          'bangumi-info-tags': true,
          'bangumi-rss-link-row': true,
          BangumiFilterField: true,
          BangumiOffsetField: true,
          AbInput: true,
          'advanced-section': true,
          NCheckbox: true,
          NSelect: true,
          NSpin: true,
        },
      },
    });

    expect(
      wrapper
        .findAll('.rule-mobile-actions .menu-label')
        .map((item) => item.text())
    ).toEqual([
      'homepage.rule.view_torrents',
      'homepage.rule.archive',
      'homepage.rule.delete',
    ]);
    expect(
      wrapper
        .get('.rule-mobile-actions .menu-stub')
        .attributes('data-placement')
    ).toBe('top');
  });

  it('should stack narrow advanced fields and enlarge review actions on mobile', () => {
    const source = readFileSync(
      new URL('../ab-edit-rule.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.weekday-row[\s\S]*?flex-direction:\s*column/
    );
    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.review-warning-actions[\s\S]*?height:\s*var\(--touch-target\)/
    );
  });
});
