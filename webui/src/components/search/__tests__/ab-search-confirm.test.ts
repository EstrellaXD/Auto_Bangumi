import { afterEach, describe, expect, it, vi } from 'vitest';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import { defineComponent, nextTick, ref } from 'vue';
import AbSearchConfirm from '../ab-search-confirm.vue';
import type { DetectOffsetResponse } from '#/bangumi';
import { ruleTemplate } from '#/bangumi';
import { apiBangumi } from '@/api/bangumi';

const isMobile = ref(true);

vi.mock('naive-ui', () => ({
  NDynamicTags: { template: '<div />' },
  NSpin: { template: '<div />' },
  useMessage: () => ({ error: vi.fn() }),
}));

vi.mock('@/api/bangumi', () => ({
  apiBangumi: {
    detectOffset: vi.fn(),
    suggestOffset: vi.fn(),
  },
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: () => ({ isMobile }),
}));

vi.mock('@/utils/poster', () => ({
  resolvePosterUrl: (link: string | null | undefined) => link ?? '',
}));

enableAutoUnmount(afterEach);

afterEach(() => {
  isMobile.value = true;
  document.body.innerHTML = '';
  vi.clearAllMocks();
});

const OffsetDialogStub = defineComponent({
  name: 'AbOffsetMismatchDialog',
  props: { show: Boolean },
  emits: ['update:show', 'apply', 'keep', 'cancel', 'after-leave'],
  template:
    '<div v-if="show" role="dialog" data-offset-dialog><button class="offset-action">offset</button></div>',
});

async function mountConfirm(season = 0) {
  const wrapper = mount(AbSearchConfirm, {
    props: {
      bangumi: {
        ...ruleTemplate,
        official_title: 'Test title',
        season,
      },
    },
    attachTo: document.body,
    global: {
      stubs: {
        AbButton: {
          emits: ['click'],
          template:
            '<button type="button" @click="$emit(\'click\')"><slot /></button>',
        },
        AbIconButton: {
          emits: ['click'],
          template:
            '<button type="button" @click="$emit(\'click\')"><slot /></button>',
        },
        AbInput: { template: '<input />' },
        AbOffsetMismatchDialog: OffsetDialogStub,
      },
    },
  });
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

function mismatchResponse() {
  vi.mocked(apiBangumi.detectOffset).mockResolvedValue({
    has_mismatch: true,
    suggestion: {
      season_offset: 1,
      episode_offset: 0,
      reason: 'Detected mismatch',
      confidence: 'high',
    },
    tmdb_info: null,
  });
}

function deferredMismatchResponse() {
  let resolveResponse: ((response: DetectOffsetResponse) => void) | null = null;
  vi.mocked(apiBangumi.detectOffset).mockImplementation(
    () =>
      new Promise<DetectOffsetResponse>((resolve) => {
        resolveResponse = resolve;
      })
  );
  return async () => {
    resolveResponse?.(mismatchResult());
    await Promise.resolve();
    await nextTick();
  };
}

function mismatchResult(): DetectOffsetResponse {
  return {
    has_mismatch: true,
    suggestion: {
      season_offset: 1,
      episode_offset: 0,
      reason: 'Detected mismatch',
      confidence: 'high',
    },
    tmdb_info: null,
  };
}

async function finishConfirmationLeave() {
  await new Promise((resolve) => setTimeout(resolve, 250));
}

describe('ab-search-confirm', () => {
  it('should connect the dialog to its visible title', async () => {
    const wrapper = await mountConfirm();

    expect(
      document.querySelector('[role="dialog"]')?.getAttribute('aria-labelledby')
    ).toBeTruthy();
    wrapper.unmount();
  });

  it('should cancel confirmation when Escape is pressed', async () => {
    const wrapper = await mountConfirm();

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );
    await new Promise((resolve) => setTimeout(resolve));

    expect(wrapper.emitted('cancel')).toHaveLength(1);
    wrapper.unmount();
  });

  it('should expose a drag affordance for the mobile sheet', async () => {
    const wrapper = await mountConfirm();

    expect(document.querySelector('.confirm-handle')).not.toBeNull();
    wrapper.unmount();
  });

  it('should move focus inside the confirmation when it opens', async () => {
    const wrapper = await mountConfirm();

    expect(
      document
        .querySelector('[role="dialog"]')
        ?.contains(document.activeElement)
    ).toBe(true);
    wrapper.unmount();
  });

  it('should keep the mobile offset dialog closed before confirmation leaves', async () => {
    const resolveMismatch = deferredMismatchResponse();
    await mountConfirm(1);
    await resolveMismatch();

    expect(document.querySelector('[data-offset-dialog]')).toBeNull();
  });

  it('should open only the offset dialog after mobile confirmation leaves', async () => {
    const resolveMismatch = deferredMismatchResponse();
    await mountConfirm(1);
    await resolveMismatch();

    await finishConfirmationLeave();

    expect({
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      offsetVisible: document.querySelector('[data-offset-dialog]') !== null,
    }).toEqual({ dialogs: 1, offsetVisible: true });
  });

  it('should keep mobile confirmation closed until offset finishes leaving', async () => {
    const resolveMismatch = deferredMismatchResponse();
    const wrapper = await mountConfirm(1);
    await resolveMismatch();
    await finishConfirmationLeave();
    wrapper.findComponent(OffsetDialogStub).vm.$emit('cancel');
    await nextTick();

    expect(document.querySelectorAll('[role="dialog"]')).toHaveLength(0);
  });

  it('should reopen mobile confirmation after offset finishes leaving', async () => {
    const resolveMismatch = deferredMismatchResponse();
    const wrapper = await mountConfirm(1);
    await resolveMismatch();
    await finishConfirmationLeave();
    const offset = wrapper.findComponent(OffsetDialogStub);
    offset.vm.$emit('cancel');
    await nextTick();

    offset.vm.$emit('after-leave');
    await nextTick();

    expect({
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      offsetVisible: document.querySelector('[data-offset-dialog]') !== null,
    }).toEqual({ dialogs: 1, offsetVisible: false });
  });

  it('should restore the original trigger after a chained mobile dialog closes', async () => {
    const trigger = document.createElement('button');
    document.body.append(trigger);
    trigger.focus();
    const resolveMismatch = deferredMismatchResponse();
    const wrapper = await mountConfirm(1);
    await resolveMismatch();
    await finishConfirmationLeave();
    const offset = wrapper.findComponent(OffsetDialogStub);
    const departingAction = wrapper.get<HTMLButtonElement>('.offset-action');
    departingAction.element.focus();
    offset.vm.$emit('cancel');
    await nextTick();

    offset.vm.$emit('after-leave');
    await nextTick();
    const finalClose = document.querySelector<HTMLButtonElement>('.close-btn');
    if (!finalClose) throw new Error('Final confirmation did not reopen');
    finalClose.click();
    wrapper.unmount();
    await nextTick();

    expect(document.activeElement === trigger).toBe(true);
    trigger.remove();
  });

  it('should reset a pending mobile handoff when the result changes', async () => {
    const resolveMismatch = deferredMismatchResponse();
    const wrapper = await mountConfirm(1);
    await resolveMismatch();

    await wrapper.setProps({
      bangumi: {
        ...ruleTemplate,
        official_title: 'Replacement title',
        season: 0,
      },
    });
    await finishConfirmationLeave();

    expect({
      confirmationVisible: document.querySelector('.confirm-modal') !== null,
      offsetVisible: document.querySelector('[data-offset-dialog]') !== null,
    }).toEqual({ confirmationVisible: true, offsetVisible: false });
  });

  it('should preserve nested confirmation and offset dialogs on desktop', async () => {
    isMobile.value = false;
    mismatchResponse();
    await mountConfirm(1);
    await flushPromises();

    expect(document.querySelectorAll('[role="dialog"]')).toHaveLength(2);
  });

  it('should sequence an open desktop offset dialog when crossing to mobile', async () => {
    isMobile.value = false;
    mismatchResponse();
    await mountConfirm(1);
    await flushPromises();

    isMobile.value = true;
    await nextTick();

    expect({
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      offsetVisible: document.querySelector('[data-offset-dialog]') !== null,
    }).toEqual({ dialogs: 1, offsetVisible: false });
  });
});
