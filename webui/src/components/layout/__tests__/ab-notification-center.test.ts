/* eslint-disable vue/one-component-per-file */
import { readFileSync } from 'node:fs';
import { defineComponent, inject, nextTick, provide, reactive, ref } from 'vue';
import type { Component, InjectionKey, Ref } from 'vue';
import { enableAutoUnmount, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { InboxMessage } from '@/api/notification';
import { useBreakpointQuery } from '@/hooks/useBreakpointQuery';
import { useNotificationStore } from '@/store/notification';
import { useMobileShellStore } from '@/store/mobile-shell';

const isMobile = ref(true);
const routerPush = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}));
vi.mock('@/hooks/useBreakpointQuery', () => ({
  useBreakpointQuery: vi.fn(),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));
vi.mock('@/store/notification', () => ({
  useNotificationStore: vi.fn(),
}));

const message: InboxMessage = {
  id: 7,
  kind: 'rss_failure',
  severity: 'warning',
  title: 'RSS refresh failed',
  body: 'A deliberately long notification body used by the mobile layout.',
  payload: null,
  read: false,
  count: 1,
  created_at: '2026-07-15T08:00:00Z',
  updated_at: '2026-07-15T08:00:00Z',
};

const notificationStore = reactive({
  messages: ref<InboxMessage[]>([message]),
  unreadCount: ref(1),
  panelOpen: ref(false),
  fetchMessages: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
  remove: vi.fn(),
  clearAll: vi.fn(),
  titleOf: (item: InboxMessage) => item.title,
  bodyOf: (item: InboxMessage) => item.body,
});

interface PopoverContext {
  open: Ref<boolean>;
  close: () => void;
  toggle: () => void;
}

const popoverContextKey: InjectionKey<PopoverContext> = Symbol('popover');

const PopoverStub = defineComponent({
  name: 'Popover',
  setup() {
    const open = ref(false);
    const close = () => {
      open.value = false;
    };
    const toggle = () => {
      open.value = !open.value;
    };
    provide(popoverContextKey, { open, close, toggle });
    return { close };
  },
  template: '<div class="popover-stub"><slot :close="close" /></div>',
});

const PopoverButtonStub = defineComponent({
  name: 'PopoverButton',
  setup() {
    return { toggle: inject(popoverContextKey)?.toggle };
  },
  template:
    '<button type="button" data-popover-trigger @click="toggle"><slot /></button>',
});

const PopoverPanelStub = defineComponent({
  name: 'PopoverPanel',
  setup() {
    return { open: inject(popoverContextKey)?.open };
  },
  template: '<section v-if="open" data-popover-panel><slot /></section>',
});

const BottomSheetStub = defineComponent({
  name: 'AbBottomSheet',
  props: {
    show: Boolean,
    title: String,
  },
  emits: ['update:show', 'after-leave'],
  template: `
    <section data-bottom-sheet :data-show="show">
      <h2 data-sheet-title>{{ title }}</h2>
      <slot />
      <button
        type="button"
        data-sheet-close
        @click="$emit('update:show', false); $emit('after-leave')"
      >close</button>
    </section>
  `,
});

const ButtonStub = defineComponent({
  name: 'AbButton',
  emits: ['click'],
  template: '<button type="button" @click="$emit(\'click\')"><slot /></button>',
});

const IconButtonStub = defineComponent({
  name: 'AbIconButton',
  props: { label: String },
  emits: ['click'],
  template:
    '<button type="button" :aria-label="label" @click="$emit(\'click\', $event)"><slot /></button>',
});

let NotificationCenter: Component;

enableAutoUnmount(afterEach);

function mountNotificationCenter() {
  return mount(NotificationCenter, {
    attachTo: document.body,
    global: {
      stubs: {
        AbBadge: true,
        AbBottomSheet: BottomSheetStub,
        AbButton: ButtonStub,
        AbIconButton: IconButtonStub,
        Popover: PopoverStub,
        PopoverButton: PopoverButtonStub,
        PopoverPanel: PopoverPanelStub,
      },
    },
  });
}

describe('ab-notification-center mobile sheet', () => {
  beforeEach(async () => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
    vi.stubGlobal('useRouter', () => ({ push: routerPush }));
    isMobile.value = true;
    notificationStore.messages = [{ ...message }];
    notificationStore.unreadCount = 1;
    notificationStore.panelOpen = false;
    vi.mocked(useBreakpointQuery).mockReturnValue({
      isMobile,
    } as ReturnType<typeof useBreakpointQuery>);
    vi.mocked(useNotificationStore).mockReturnValue(
      notificationStore as unknown as ReturnType<typeof useNotificationStore>
    );
    useMobileShellStore().closeOverlay();
    NotificationCenter = (await import('../ab-notification-center.vue'))
      .default;
  });

  it('should open the notifications overlay when the mobile bell is pressed', async () => {
    const wrapper = mountNotificationCenter();

    await wrapper.get('.notification-bell').trigger('click');

    expect(useMobileShellStore().activeOverlay).toBe('notifications');
  });

  it('should show the bottom sheet when the notifications overlay is active', async () => {
    const wrapper = mountNotificationCenter();

    useMobileShellStore().openOverlay('notifications');
    await nextTick();

    expect(wrapper.get('[data-bottom-sheet]').attributes('data-show')).toBe(
      'true'
    );
  });

  it('should fetch messages once when the mobile sheet opens', async () => {
    mountNotificationCenter();
    notificationStore.fetchMessages.mockClear();

    useMobileShellStore().openOverlay('notifications');
    await nextTick();

    expect(notificationStore.fetchMessages).toHaveBeenCalledTimes(1);
  });

  it('should render notification activation as a native button', async () => {
    const wrapper = mountNotificationCenter();

    useMobileShellStore().openOverlay('notifications');
    await nextTick();

    expect(wrapper.get('.notification-item-action').element.tagName).toBe(
      'BUTTON'
    );
  });

  it('should mark a message read when its native action is pressed', async () => {
    const wrapper = mountNotificationCenter();

    useMobileShellStore().openOverlay('notifications');
    await nextTick();
    await wrapper.get('.notification-item-action').trigger('click');

    expect(notificationStore.markRead).toHaveBeenCalledWith(7);
  });

  it('should remove a message without activating its route', async () => {
    const wrapper = mountNotificationCenter();

    useMobileShellStore().openOverlay('notifications');
    await nextTick();
    await wrapper.get('.notification-delete').trigger('click');

    expect(notificationStore.remove).toHaveBeenCalledWith(7);
  });

  it('should restore focus after the mobile sheet finishes leaving', async () => {
    const wrapper = mountNotificationCenter();
    const trigger = wrapper.get<HTMLButtonElement>('.notification-bell');

    await trigger.trigger('click');
    await wrapper.get('[data-sheet-close]').trigger('click');
    await nextTick();

    expect(document.activeElement).toBe(trigger.element);
  });

  it('should keep the Popover panel on tablet and desktop', async () => {
    isMobile.value = false;

    const wrapper = mountNotificationCenter();
    await wrapper.get('[data-popover-trigger]').trigger('click');

    expect(wrapper.find('[data-popover-panel]').exists()).toBe(true);
  });

  it('should not repeat the bottom sheet title inside the mobile content', () => {
    const wrapper = mountNotificationCenter();

    expect(wrapper.find('.notification-head-title').exists()).toBe(false);
  });

  it('should reset an open desktop Popover after crossing the phone breakpoint', async () => {
    isMobile.value = false;
    const wrapper = mountNotificationCenter();
    await wrapper.get('[data-popover-trigger]').trigger('click');

    isMobile.value = true;
    await nextTick();
    isMobile.value = false;
    await nextTick();

    expect(wrapper.find('[data-popover-panel]').exists()).toBe(false);
  });

  it('should use the phone touch target for notification deletion', () => {
    const source = readFileSync(
      new URL('../ab-notification-center.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.notification-delete\s*\{[\s\S]*?min-width:\s*var\(--touch-target\)[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });

  it('should contain horizontal overflow inside the mobile sheet', () => {
    const source = readFileSync(
      new URL('../ab-notification-center.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.notification-panel-inner\s*\{[\s\S]*?overflow-x:\s*hidden/
    );
  });
});
