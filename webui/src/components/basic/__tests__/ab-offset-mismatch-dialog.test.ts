import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import {
  Dialog as HeadlessDialog,
  DialogPanel as HeadlessDialogPanel,
  DialogTitle as HeadlessDialogTitle,
} from '@headlessui/vue';
import { mount } from '@vue/test-utils';
import AbOffsetMismatchDialog from '../ab-offset-mismatch-dialog.vue';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

const AbButtonStub = {
  emits: ['click'],
  template:
    '<button type="button" @click="$emit(\'click\', $event)"><slot /></button>',
};

afterEach(() => {
  document.body.innerHTML = '';
});

async function mountDialog() {
  const wrapper = mount(AbOffsetMismatchDialog, {
    props: {
      show: true,
      bangumiTitle: 'Test title',
      parsedSeason: 1,
      parsedEpisode: 3,
      tmdbInfo: {
        title: 'Test title',
        total_seasons: 2,
        season_episode_counts: { 1: 12, 2: 10 },
        status: null,
      },
      suggestion: {
        season_offset: 1,
        episode_offset: 2,
        reason: 'Detected a mismatch',
        confidence: 'high',
      },
    },
    attachTo: document.body,
    global: {
      stubs: {
        AbButton: AbButtonStub,
      },
    },
  });
  await new Promise((resolve) => setTimeout(resolve));
  return wrapper;
}

async function mountNestedDialog(outerClose: () => void) {
  const Host = {
    components: {
      AbOffsetMismatchDialog,
      HeadlessDialog,
      HeadlessDialogPanel,
      HeadlessDialogTitle,
    },
    setup() {
      const showOffset = ref(false);
      return { outerClose, showOffset };
    },
    template: `
      <HeadlessDialog :open="true" @close="outerClose">
        <HeadlessDialogPanel>
          <HeadlessDialogTitle>Parent confirmation</HeadlessDialogTitle>
          <button id="open-offset" type="button" @click="showOffset = true">
            Open offset
          </button>
        </HeadlessDialogPanel>
        <AbOffsetMismatchDialog
          v-model:show="showOffset"
          bangumi-title="Test title"
          :parsed-season="1"
          :parsed-episode="3"
          :tmdb-info="null"
          :suggestion="null"
        />
      </HeadlessDialog>
    `,
  };
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: { stubs: { AbButton: AbButtonStub } },
  });
  await new Promise((resolve) => setTimeout(resolve));
  const openButton = document.querySelector<HTMLButtonElement>('#open-offset');
  if (!openButton) throw new Error('Nested dialog trigger should be rendered');
  openButton.focus();
  openButton.click();
  await new Promise((resolve) => setTimeout(resolve));
  return { openButton, wrapper };
}

function dispatchOutsideClick(element: Element) {
  for (const type of ['pointerdown', 'mousedown', 'click']) {
    element.dispatchEvent(
      new MouseEvent(type, { bubbles: true, cancelable: true })
    );
  }
}

function clickButton(label: string) {
  const button = Array.from(document.querySelectorAll('button')).find(
    (candidate) => candidate.textContent?.trim() === label
  );
  if (!button) throw new Error(`Button "${label}" should be rendered`);
  button.click();
}

function waitForDialogLeave() {
  return new Promise<void>((resolve) => setTimeout(resolve, 250));
}

describe('ab-offset-mismatch-dialog', () => {
  it('should expose its visible title as the dialog accessible name', async () => {
    const wrapper = await mountDialog();
    const dialog = document.querySelector('[role="dialog"]');
    const labelledBy = dialog?.getAttribute('aria-labelledby');
    const title = labelledBy ? document.getElementById(labelledBy) : null;

    expect({
      labelledBy: Boolean(labelledBy),
      title: title?.textContent,
    }).toEqual({
      labelledBy: true,
      title: 'offset.dialog_title',
    });
    wrapper.unmount();
  });

  it('should cancel when Escape is pressed', async () => {
    const wrapper = await mountDialog();

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );
    await waitForDialogLeave();

    expect({
      cancel: wrapper.emitted('cancel'),
      updateShow: wrapper.emitted('update:show'),
    }).toEqual({ cancel: [[]], updateShow: [[false]] });
    wrapper.unmount();
  });

  it('should cancel when the backdrop is clicked', async () => {
    const wrapper = await mountDialog();
    const backdrop = document.querySelector('.dialog-backdrop');
    if (!backdrop) throw new Error('Dialog backdrop should be rendered');

    dispatchOutsideClick(backdrop);
    await waitForDialogLeave();

    expect({
      cancel: wrapper.emitted('cancel'),
      updateShow: wrapper.emitted('update:show'),
    }).toEqual({ cancel: [[]], updateShow: [[false]] });
    wrapper.unmount();
  });

  it('should keep the parent dialog open when the nested dialog closes', async () => {
    const outerClose = vi.fn();
    const { wrapper } = await mountNestedDialog(outerClose);
    const closeButton = document.querySelector<HTMLButtonElement>('.close-btn');
    if (!closeButton)
      throw new Error('Nested dialog close action should render');

    closeButton.click();
    await waitForDialogLeave();

    expect(outerClose).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('should restore parent focus when the nested dialog is closed', async () => {
    const { openButton, wrapper } = await mountNestedDialog(() => undefined);
    const closeButton = document.querySelector<HTMLButtonElement>('.close-btn');
    if (!closeButton)
      throw new Error('Nested dialog close action should render');

    closeButton.click();
    await waitForDialogLeave();

    expect((document.activeElement as HTMLElement | null)?.id).toBe(
      openButton.id
    );
    wrapper.unmount();
  });

  it('should emit edited offsets and close when applying the suggestion', async () => {
    const wrapper = await mountDialog();
    const [seasonInput, episodeInput] = Array.from(
      document.querySelectorAll<HTMLInputElement>('.offset-input')
    );
    seasonInput.value = '-1';
    seasonInput.dispatchEvent(new Event('input', { bubbles: true }));
    episodeInput.value = '4';
    episodeInput.dispatchEvent(new Event('input', { bubbles: true }));

    clickButton('offset.apply');
    await waitForDialogLeave();

    expect({
      apply: wrapper.emitted('apply'),
      updateShow: wrapper.emitted('update:show'),
    }).toEqual({
      apply: [[{ seasonOffset: -1, episodeOffset: 4 }]],
      updateShow: [[false]],
    });
    wrapper.unmount();
  });

  it('should preserve parsed and adjusted values when rendering the preview', async () => {
    const wrapper = await mountDialog();

    expect([
      document.querySelector('.preview-from')?.textContent,
      document.querySelector('.preview-to')?.textContent,
    ]).toEqual(['S01E03', 'S02E05']);
    wrapper.unmount();
  });

  it('should emit keep and close when keeping the original values', async () => {
    const wrapper = await mountDialog();

    clickButton('offset.keep');
    await waitForDialogLeave();

    expect({
      keep: wrapper.emitted('keep'),
      updateShow: wrapper.emitted('update:show'),
    }).toEqual({ keep: [[]], updateShow: [[false]] });
    wrapper.unmount();
  });

  it('should signal when its closing transition finishes', async () => {
    const wrapper = await mountDialog();

    await wrapper.setProps({ show: false });
    await waitForDialogLeave();

    expect(wrapper.emitted('after-leave')).toHaveLength(1);
    wrapper.unmount();
  });

  it('should refresh editable values when the suggestion changes', async () => {
    const wrapper = await mountDialog();

    await wrapper.setProps({
      suggestion: {
        season_offset: -2,
        episode_offset: 5,
        reason: 'Updated mismatch',
        confidence: 'medium',
      },
    });

    expect(
      Array.from(
        document.querySelectorAll<HTMLInputElement>('.offset-input')
      ).map((input) => input.value)
    ).toEqual(['-2', '5']);
    wrapper.unmount();
  });

  it('should use a safe-area bounded bottom sheet below 640px', () => {
    const source = readFileSync(
      new URL('../ab-offset-mismatch-dialog.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.dialog-backdrop\s*\{[\s\S]*?align-items:\s*flex-end[\s\S]*?\.dialog-modal\s*\{[\s\S]*?max-height:\s*calc\([\s\S]*?100dvh[\s\S]*?env\(safe-area-inset-top\)[\s\S]*?env\(safe-area-inset-bottom\)[\s\S]*?\)/
    );
  });

  it('should enforce 44px mobile targets for close and offset inputs', () => {
    const source = readFileSync(
      new URL('../ab-offset-mismatch-dialog.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.close-btn\s*\{[\s\S]*?width:\s*var\(--touch-target\)[\s\S]*?height:\s*var\(--touch-target\)[\s\S]*?\.offset-input\s*\{[\s\S]*?height:\s*var\(--touch-target\)/
    );
  });
});
