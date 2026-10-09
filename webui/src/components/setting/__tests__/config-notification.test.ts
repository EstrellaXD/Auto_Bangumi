import { flushPromises, mount } from '@vue/test-utils';
import { ref } from 'vue';
import ConfigNotification from '../config-notification.vue';
import { apiNotification } from '@/api/notification';

vi.mock('@/api/notification', () => ({
  apiNotification: { testProviderConfig: vi.fn(), testProvider: vi.fn() },
}));
vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn() }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string, p?: { id?: string }) => (p?.id ? `${key}:${p.id}` : key),
    returnUserLangText: (m: Record<string, string>) => m.en,
  }),
}));
vi.mock('@/hooks/usePluginProviders', () => ({
  usePluginProviders: () => ref({ notifier: ['ntfy'] }),
}));
const group = ref({
  enable: true,
  providers: [
    { type: 'telegram', enabled: true, token: '********' },
    { type: 'ntfy', enabled: true, topic: '********' },
  ],
});
const saved = { notification: { providers: [] as unknown[] } };
vi.mock('@/store/config', () => ({
  useConfigStore: () => ({ getSettingGroup: () => group, savedConfig: saved }),
}));

const api = vi.mocked(apiNotification);

function mountPage() {
  return mount(ConfigNotification, {
    global: {
      mocks: { $t: (k: string) => k },
      stubs: {
        'ab-fold-panel': { template: '<section><slot /></section>' },
        'ab-setting': true,
        'ab-field': { template: '<div><slot /></div>' },
        'ab-input': true,
        'ab-icon-button': {
          props: ['label'],
          template: '<button :aria-label="label"><slot /></button>',
        },
        'ab-button': { template: '<button><slot /></button>' },
        'ab-modal': {
          props: ['show'],
          template: '<div v-if="show"><slot /><slot name="footer" /></div>',
        },
        NSelect: {
          props: ['value'],
          template: '<select class="type" />',
        },
      },
    },
  });
}

const ok = { data: { success: true, message_en: 'ok', message_zh: '好' } };

describe('config-notification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.testProviderConfig.mockResolvedValue(ok as any);
    api.testProvider.mockResolvedValue(ok as any);
    saved.notification.providers = JSON.parse(
      JSON.stringify(group.value.providers)
    );
  });

  // /config/get 返回的密钥是掩码，列表测试须按下标走后端保存的配置
  it.each([
    [0, 'Telegram: ok'],
    [1, 'config.notification_set.plugin_label:ntfy: ok'],
  ])(
    'should test saved row %i by index when testing from the list',
    async (index, text) => {
      const w = mountPage();
      await w
        .findAll('[aria-label="config.notification_set.test"]')
        [index].trigger('click');
      await flushPromises();
      expect(api.testProviderConfig).not.toHaveBeenCalled();
      expect(api.testProvider).toHaveBeenCalledWith({ provider_index: index });
      expect(w.find('.test-result').text()).toBe(text);
    }
  );

  // 未保存的行（新增或删除后下标错位）在后端没有对应项，按当前配置测试
  it('should test an unsaved row with its in-memory config', async () => {
    saved.notification.providers = [];
    const w = mountPage();
    await w
      .find('[aria-label="config.notification_set.test"]')
      .trigger('click');
    await flushPromises();
    expect(api.testProvider).not.toHaveBeenCalled();
    expect(api.testProviderConfig).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'telegram' })
    );
  });

  it('should keep dialog test results out of the list and clear them on close', async () => {
    const w = mountPage();
    const add = w
      .findAll('button')
      .find((b) => b.text() === 'config.notification_set.add_provider')!;
    await add.trigger('click');
    const test = w
      .findAll('button')
      .find((b) => b.text() === 'config.notification_set.test')!;
    await test.trigger('click');
    await flushPromises();
    expect(w.findAll('.test-result')).toHaveLength(1);
    const cancel = w
      .findAll('button')
      .find((b) => b.text() === 'config.cancel')!;
    await cancel.trigger('click');
    await flushPromises();
    expect(w.find('.test-result').exists()).toBe(false);
  });

  it('should show a credentials hint and no Test button for plugin types', async () => {
    const w = mountPage();
    const add = w
      .findAll('button')
      .find((b) => b.text() === 'config.notification_set.add_provider')!;
    await add.trigger('click');
    expect(w.find('.plugin-hint').exists()).toBe(false);
    (w.vm as any).newProvider.type = 'ntfy';
    await flushPromises();
    expect(w.find('.plugin-hint').exists()).toBe(true);
    expect(
      w
        .findAll('button')
        .some((b) => b.text() === 'config.notification_set.test')
    ).toBe(false);
  });
});
