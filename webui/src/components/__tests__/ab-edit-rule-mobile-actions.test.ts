/* eslint-disable vue/one-component-per-file */
import { readFileSync } from 'node:fs';
import { enableAutoUnmount, mount } from '@vue/test-utils';
import { defineComponent, ref } from 'vue';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AbEditRule from '../ab-edit-rule.vue';
import AbModal from '../basic/ab-modal.vue';
import { mockBangumiRule } from '@/test/mocks/api';

const isMobile = ref(true);

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
  useBreakpointQuery: () => ({ isMobile }),
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
      <button
        v-for="item in items"
        :key="item.key"
        type="button"
        class="menu-label"
        :data-menu-item="item.key"
        @click="item.handler?.()"
      >
        {{ typeof item.label === 'function' ? item.label() : item.label }}
      </button>
    </div>
  `,
});

const ButtonStub = defineComponent({
  emits: ['click'],
  template:
    '<button type="button" @click="$emit(\'click\', $event)"><slot /></button>',
});

const IconButtonStub = defineComponent({
  props: { label: String },
  emits: ['click'],
  template:
    '<button type="button" :aria-label="label" @click="$emit(\'click\', $event)"><slot /></button>',
});

const flowStubs = {
  'ab-menu': MenuStub,
  'ab-icon-button': IconButtonStub,
  'ab-button': ButtonStub,
  'bangumi-preview': true,
  'bangumi-info-tags': true,
  'bangumi-rss-link-row': true,
  BangumiFilterField: true,
  BangumiOffsetField: true,
  AbInput: true,
  'advanced-section': true,
  NCheckbox: defineComponent({
    template: '<label><input type="checkbox" /><slot /></label>',
  }),
  NSelect: true,
  NSpin: true,
};

enableAutoUnmount(afterEach);

beforeEach(() => {
  isMobile.value = true;
});

afterEach(() => {
  document.body.innerHTML = '';
});

async function mountEditFlow() {
  const Host = defineComponent({
    components: { AbEditRule },
    setup() {
      const show = ref(true);
      const rule = ref({ ...mockBangumiRule });
      return { rule, show };
    },
    template: '<AbEditRule v-model:show="show" v-model:rule="rule" />',
  });
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: {
      components: { AbModal },
      stubs: flowStubs,
    },
  });
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

async function openDeleteStep() {
  const deleteAction = document.querySelector<HTMLButtonElement>(
    '[data-menu-item="delete"]'
  );
  if (!deleteAction) throw new Error('Mobile delete action should render');
  deleteAction.click();
  await new Promise((resolve) => setTimeout(resolve));
}

function clickButton(label: string) {
  const button = Array.from(document.querySelectorAll('button')).find(
    (candidate) => candidate.textContent?.trim() === label
  );
  if (!button) throw new Error(`Button "${label}" should render`);
  button.click();
}

function dispatchOutsideClick(element: Element) {
  for (const type of ['pointerdown', 'mousedown', 'click']) {
    element.dispatchEvent(
      new MouseEvent(type, { bubbles: true, cancelable: true })
    );
  }
}

async function waitForDialogLeave() {
  await new Promise((resolve) => setTimeout(resolve, 250));
}

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

  it('should replace the mobile editor with delete content inside one dialog', async () => {
    await mountEditFlow();

    await openDeleteStep();

    expect({
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      deleteVisible: document.querySelector('.delete-message') !== null,
      editorVisible: document.querySelector('.edit-content') !== null,
    }).toEqual({ dialogs: 1, deleteVisible: true, editorVisible: false });
  });

  it('should restore the mobile More trigger after cancelling delete', async () => {
    await mountEditFlow();
    await openDeleteStep();

    clickButton('homepage.rule.cancel_btn');
    await waitForDialogLeave();

    expect(document.activeElement).toBe(
      document.querySelector('.rule-mobile-actions button')
    );
  });

  it('should return to the mobile editor when Escape closes delete', async () => {
    const wrapper = await mountEditFlow();
    await openDeleteStep();

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );
    await waitForDialogLeave();

    expect({
      editorOpen: (wrapper.vm as { show: boolean }).show,
      deleteVisible: document.querySelector('.delete-message') !== null,
      focusRestored:
        document.activeElement ===
        document.querySelector('.rule-mobile-actions button'),
    }).toEqual({ editorOpen: true, deleteVisible: false, focusRestored: true });
  });

  it('should return to the mobile editor when the delete backdrop is pressed', async () => {
    const wrapper = await mountEditFlow();
    await openDeleteStep();
    const backdrops = document.querySelectorAll('.ab-bottom-sheet__backdrop');
    const backdrop = backdrops.item(backdrops.length - 1);
    if (!backdrop) throw new Error('Mobile delete backdrop should render');

    dispatchOutsideClick(backdrop);
    await waitForDialogLeave();

    expect({
      editorOpen: (wrapper.vm as { show: boolean }).show,
      deleteVisible: document.querySelector('.delete-message') !== null,
      focusRestored:
        document.activeElement ===
        document.querySelector('.rule-mobile-actions button'),
    }).toEqual({ editorOpen: true, deleteVisible: false, focusRestored: true });
  });

  it('should preserve the nested delete dialog on tablet and desktop', async () => {
    isMobile.value = false;
    await mountEditFlow();

    clickButton('homepage.rule.delete');
    await new Promise((resolve) => setTimeout(resolve));

    expect(document.querySelectorAll('[role="dialog"]')).toHaveLength(2);
  });
});
