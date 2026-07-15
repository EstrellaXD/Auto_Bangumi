import { createPinia, setActivePinia } from 'pinia';
import type { Pinia } from 'pinia';
import type { Component, ComponentPublicInstance } from 'vue';
import { watch } from 'vue';
import {
  type DOMWrapper,
  type VueWrapper,
  enableAutoUnmount,
  flushPromises,
  mount,
} from '@vue/test-utils';
import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import AbContainer from '@/components/ab-container.vue';
import AbButton from '@/components/basic/ab-button.vue';
import AbField from '@/components/basic/ab-field.vue';
import { useSetupStore } from '@/store/setup';

const apiComplete = vi.fn();
const markSetupComplete = vi.fn();
const routerPush = vi.fn();

vi.mock('@/api/setup', () => ({
  apiSetup: {
    complete: apiComplete,
    testDownloader: vi.fn(),
    testNotification: vi.fn(),
    testRSS: vi.fn(),
  },
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string) => key,
    returnUserLangText: (texts: { en: string; 'zh-CN': string }) => texts.en,
  }),
}));

vi.mock('@/router', () => ({ markSetupComplete }));

let AccountStep: Component;
let DownloaderStep: Component;
let NotificationStep: Component;
let ReviewStep: Component;
let RSSStep: Component;
let pinia: Pinia;

enableAutoUnmount(afterEach);

function mountStep(component: Component): VueWrapper<ComponentPublicInstance> {
  return mount(component, {
    global: {
      plugins: [pinia],
      components: { AbButton, AbContainer, AbField },
    },
  });
}

function getButton(
  wrapper: VueWrapper<ComponentPublicInstance>,
  label: string
): DOMWrapper<HTMLButtonElement> {
  const button = wrapper
    .findAll<HTMLButtonElement>('button')
    .find((candidate) => candidate.text().trim() === label);

  if (!button) throw new Error(`Button not found: ${label}`);
  return button;
}

async function fillAccount(
  wrapper: VueWrapper<ComponentPublicInstance>,
  values: { username: string; password: string; confirmation: string }
): Promise<void> {
  await wrapper
    .get<HTMLInputElement>('input[aria-label="setup.account.username"]')
    .setValue(values.username);
  await wrapper
    .get<HTMLInputElement>('input[aria-label="setup.account.password"]')
    .setValue(values.password);
  await wrapper
    .get<HTMLInputElement>('input[aria-label="setup.account.confirm_password"]')
    .setValue(values.confirmation);
}

beforeAll(async () => {
  vi.stubGlobal('useRouter', () => ({ push: routerPush }));
  [AccountStep, DownloaderStep, NotificationStep, ReviewStep, RSSStep] =
    await Promise.all([
      import('../wizard-step-account.vue').then((module) => module.default),
      import('../wizard-step-downloader.vue').then((module) => module.default),
      import('../wizard-step-notification.vue').then(
        (module) => module.default
      ),
      import('../wizard-step-review.vue').then((module) => module.default),
      import('../wizard-step-rss.vue').then((module) => module.default),
    ]);
});

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  pinia = createPinia();
  setActivePinia(pinia);
  apiComplete.mockResolvedValue({ msg_en: 'Success', msg_zh: '成功' });
});

describe('setup store navigation', () => {
  it('should navigate through the exact setup step order', () => {
    const store = useSetupStore();
    const visited = [store.currentStep];

    for (let index = 1; index < store.steps.length; index++) {
      store.nextStep();
      visited.push(store.currentStep);
    }

    expect(visited).toEqual([
      'welcome',
      'account',
      'downloader',
      'rss',
      'notification',
      'review',
    ]);
  });
});

describe('account step validation', () => {
  it('should reject a username shorter than four characters', async () => {
    const store = useSetupStore();
    store.goToStep(1);
    const wrapper = mountStep(AccountStep);

    await fillAccount(wrapper, {
      username: 'abc',
      password: '12345678',
      confirmation: '12345678',
    });

    expect(getButton(wrapper, 'setup.nav.next').attributes('disabled')).toBe(
      ''
    );
  });

  it('should reject a password shorter than eight characters', async () => {
    const store = useSetupStore();
    store.goToStep(1);
    const wrapper = mountStep(AccountStep);

    await fillAccount(wrapper, {
      username: 'admin',
      password: '1234567',
      confirmation: '1234567',
    });

    expect(getButton(wrapper, 'setup.nav.next').attributes('disabled')).toBe(
      ''
    );
  });

  it('should reject passwords that do not match', async () => {
    const store = useSetupStore();
    store.goToStep(1);
    const wrapper = mountStep(AccountStep);

    await fillAccount(wrapper, {
      username: 'admin',
      password: '12345678',
      confirmation: '87654321',
    });

    expect(getButton(wrapper, 'setup.nav.next').attributes('disabled')).toBe(
      ''
    );
  });

  it('should advance when all account thresholds are met', async () => {
    const store = useSetupStore();
    store.goToStep(1);
    const wrapper = mountStep(AccountStep);

    await fillAccount(wrapper, {
      username: 'user',
      password: '12345678',
      confirmation: '12345678',
    });
    await getButton(wrapper, 'setup.nav.next').trigger('click');

    expect(store.currentStep).toBe('downloader');
  });
});

describe('downloader step progression', () => {
  it('should block continuation while the host is empty', () => {
    const store = useSetupStore();
    store.goToStep(2);
    const wrapper = mountStep(DownloaderStep);

    expect(getButton(wrapper, 'setup.nav.next').attributes('disabled')).toBe(
      ''
    );
  });

  it('should advance with only a host and no successful connection test', async () => {
    const store = useSetupStore();
    store.goToStep(2);
    store.validation.downloaderTested = false;
    const wrapper = mountStep(DownloaderStep);

    await wrapper
      .get<HTMLInputElement>('input[aria-label="config.downloader_set.host"]')
      .setValue('qbittorrent:8080');
    await getButton(wrapper, 'setup.nav.next').trigger('click');

    expect({
      currentStep: store.currentStep,
      downloaderTested: store.validation.downloaderTested,
    }).toEqual({ currentStep: 'rss', downloaderTested: false });
  });
});

describe('optional setup steps', () => {
  it('should mark RSS skipped before advancing', async () => {
    const store = useSetupStore();
    store.goToStep(3);
    let skippedWhenStepChanged: boolean | undefined;
    const stopWatching = watch(
      () => store.currentStep,
      () => {
        skippedWhenStepChanged = store.rssData.skipped;
      },
      { flush: 'sync' }
    );
    const wrapper = mountStep(RSSStep);

    await getButton(wrapper, 'setup.nav.skip').trigger('click');
    stopWatching();

    expect({ skippedWhenStepChanged, currentStep: store.currentStep }).toEqual({
      skippedWhenStepChanged: true,
      currentStep: 'notification',
    });
  });

  it('should mark notifications skipped before advancing', async () => {
    const store = useSetupStore();
    store.goToStep(4);
    let skippedWhenStepChanged: boolean | undefined;
    const stopWatching = watch(
      () => store.currentStep,
      () => {
        skippedWhenStepChanged = store.notificationData.skipped;
      },
      { flush: 'sync' }
    );
    const wrapper = mountStep(NotificationStep);

    await getButton(wrapper, 'setup.nav.skip').trigger('click');
    stopWatching();

    expect({ skippedWhenStepChanged, currentStep: store.currentStep }).toEqual({
      skippedWhenStepChanged: true,
      currentStep: 'review',
    });
  });
});

describe('setup completion', () => {
  it('should complete, reset, mark setup done, and route explicitly to Login', async () => {
    const events: string[] = [];
    const store = useSetupStore();
    store.goToStep(5);
    store.accountData.username = 'admin';
    store.accountData.password = '12345678';
    store.downloaderData.host = 'qbittorrent:8080';
    apiComplete.mockImplementation(async () => {
      events.push('api');
      return { msg_en: 'Success', msg_zh: '成功' };
    });
    const resetStore = store.$reset;
    vi.spyOn(store, '$reset').mockImplementation(() => {
      events.push('reset');
      resetStore();
    });
    markSetupComplete.mockImplementation(() => {
      events.push('mark');
    });
    routerPush.mockImplementation((target: unknown) => {
      events.push(`route:${(target as { name?: string }).name ?? ''}`);
    });
    const wrapper = mountStep(ReviewStep);

    await getButton(wrapper, 'setup.review.complete').trigger('click');
    await flushPromises();

    expect(events).toEqual(['api', 'reset', 'mark', 'route:Login']);
  });
});
