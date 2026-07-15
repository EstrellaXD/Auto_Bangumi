/* eslint-disable vue/one-component-per-file */
import { defineComponent, ref } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AbMobileMoreSheet from '../ab-mobile-more-sheet.vue';
import { useAddRss } from '@/hooks/useAddRss';
import { useAppInfo } from '@/hooks/useAppInfo';
import { useAuth } from '@/hooks/useAuth';
import { useConfirm } from '@/hooks/useConfirm';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useMyI18n } from '@/hooks/useMyI18n';
import { useProgramStore } from '@/store/program';

vi.mock('@/hooks/useAddRss', () => ({ useAddRss: vi.fn() }));
vi.mock('@/hooks/useAppInfo', () => ({ useAppInfo: vi.fn() }));
vi.mock('@/hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('@/hooks/useConfirm', () => ({ useConfirm: vi.fn() }));
vi.mock('@/hooks/useDarkMode', () => ({ useDarkMode: vi.fn() }));
vi.mock('@/hooks/useMyI18n', () => ({ useMyI18n: vi.fn() }));
vi.mock('@/store/program', () => ({ useProgramStore: vi.fn() }));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: String, required: true } },
  emits: ['click'],
  template: '<a :href="to" @click="$emit(\'click\')"><slot /></a>',
});

const BottomSheetStub = defineComponent({
  name: 'AbBottomSheet',
  props: { show: Boolean, title: String },
  emits: ['update:show'],
  template:
    '<section v-if="show" class="sheet-stub" :data-title="title"><slot /></section>',
});

const actions = {
  changeLocale: vi.fn(),
  confirm: vi.fn(),
  logout: vi.fn(),
  openAddRss: vi.fn(),
  pause: vi.fn(),
  resetRule: vi.fn(),
  restart: vi.fn(),
  shutdown: vi.fn(),
  start: vi.fn(),
  toggleDark: vi.fn(),
};

function mountSheet(running = false, statusKnown = true) {
  vi.mocked(useAppInfo).mockReturnValue({
    running: ref(running),
    statusKnown: ref(statusKnown),
  } as ReturnType<typeof useAppInfo>);

  return mount(AbMobileMoreSheet, {
    props: { show: true },
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        AbBottomSheet: BottomSheetStub,
        AbAddRss: true,
        AbChangeAccount: true,
      },
    },
  });
}

describe('ab-mobile-more-sheet', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAddRss).mockReturnValue({
      showAddRss: ref(false),
      openAddRss: actions.openAddRss,
      closeAddRss: vi.fn(),
    });
    vi.mocked(useAuth).mockReturnValue({
      logout: actions.logout,
    } as unknown as ReturnType<typeof useAuth>);
    vi.mocked(useConfirm).mockReturnValue({
      confirm: actions.confirm,
    } as ReturnType<typeof useConfirm>);
    vi.mocked(useDarkMode).mockReturnValue({
      isDark: ref(false),
      toggle: actions.toggleDark,
    } as unknown as ReturnType<typeof useDarkMode>);
    vi.mocked(useMyI18n).mockReturnValue({
      t: (key: string) => key,
      changeLocale: actions.changeLocale,
    } as unknown as ReturnType<typeof useMyI18n>);
    vi.mocked(useProgramStore).mockReturnValue({
      start: actions.start,
      pause: actions.pause,
      restart: actions.restart,
      shutdown: actions.shutdown,
      resetRule: actions.resetRule,
    } as unknown as ReturnType<typeof useProgramStore>);
    actions.confirm.mockResolvedValue(true);
  });

  it('should expose every management page when the sheet is open', () => {
    const wrapper = mountSheet();

    expect(wrapper.findAll('.mobile-more__route')).toHaveLength(7);
  });

  it('should expose Downloader when no legacy feature flag is set', () => {
    const wrapper = mountSheet();

    expect(wrapper.find('a[href="/downloader"]').exists()).toBe(true);
  });

  it('should use an accessible title when the sheet is open', () => {
    const wrapper = mountSheet();

    expect(wrapper.find('.sheet-stub').attributes('data-title')).toBe(
      'common.moreActions'
    );
  });

  it('should switch theme when the theme action is pressed', async () => {
    const wrapper = mountSheet();

    await wrapper.find('[data-action="theme"]').trigger('click');

    expect(actions.toggleDark).toHaveBeenCalledTimes(1);
  });

  it('should switch locale when the locale action is pressed', async () => {
    const wrapper = mountSheet();

    await wrapper.find('[data-action="locale"]').trigger('click');

    expect(actions.changeLocale).toHaveBeenCalledTimes(1);
  });

  it('should start the program when the program is stopped', async () => {
    const wrapper = mountSheet(false);

    await wrapper.find('[data-action="program-toggle"]').trigger('click');

    expect(actions.start).toHaveBeenCalledTimes(1);
  });

  it('should pause the program when the program is running', async () => {
    const wrapper = mountSheet(true);

    await wrapper.find('[data-action="program-toggle"]').trigger('click');

    expect(actions.pause).toHaveBeenCalledTimes(1);
  });

  it('should disable the program toggle before status is known', () => {
    const wrapper = mountSheet(false, false);

    expect(
      wrapper.find<HTMLButtonElement>('[data-action="program-toggle"]').element
        .disabled
    ).toBe(true);
  });

  it('should run restart when the restart confirmation succeeds', async () => {
    const wrapper = mountSheet();

    await wrapper.find('[data-action="restart"]').trigger('click');
    await flushPromises();

    expect(actions.restart).toHaveBeenCalledTimes(1);
  });

  it('should preserve the program when the restart confirmation is cancelled', async () => {
    actions.confirm.mockResolvedValue(false);
    const wrapper = mountSheet();

    await wrapper.find('[data-action="restart"]').trigger('click');
    await flushPromises();

    expect(actions.restart).not.toHaveBeenCalled();
  });

  it('should close More before a destructive confirmation opens', async () => {
    let closedBeforeConfirm = false;
    const wrapper = mountSheet();
    actions.confirm.mockImplementation(async () => {
      closedBeforeConfirm =
        wrapper.emitted('update:show')?.some(([value]) => value === false) ??
        false;
      return false;
    });

    await wrapper.find('[data-action="restart"]').trigger('click');
    await flushPromises();

    expect(closedBeforeConfirm).toBe(true);
  });

  it('should request confirmation when logout is pressed', async () => {
    const wrapper = mountSheet();

    await wrapper.find('[data-action="logout"]').trigger('click');
    await flushPromises();

    expect(actions.confirm).toHaveBeenCalledTimes(1);
  });
});
