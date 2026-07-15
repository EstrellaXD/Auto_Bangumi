/* eslint-disable vue/one-component-per-file -- inline stubs keep this component test self-contained */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  type ComponentPublicInstance,
  KeepAlive,
  defineComponent,
  nextTick,
  ref,
} from 'vue';
import {
  type DOMWrapper,
  type VueWrapper,
  flushPromises,
  mount,
} from '@vue/test-utils';
import ConfigAccess from '../config-access.vue';
import { apiTokens, apiUsers } from '@/api/access';
import type { ApiTokenCreated, ApiTokenPublic, UserPublic } from '#/access';

vi.mock('@/api/access', () => ({
  apiUsers: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
  apiTokens: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
  },
}));

vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  }),
}));

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('@/hooks/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

const users: UserPublic[] = [
  {
    id: 1,
    username: 'alice',
    enabled: true,
    created_at: '2026-07-01T08:00:00Z',
    updated_at: '2026-07-01T08:00:00Z',
  },
  {
    id: 2,
    username: 'bob',
    enabled: true,
    created_at: '2026-07-02T08:00:00Z',
    updated_at: '2026-07-02T08:00:00Z',
  },
];

const tokens: ApiTokenPublic[] = [
  {
    id: 1,
    user_id: 1,
    name: 'active-token',
    scope: 'api',
    prefix: 'ab_api_act',
    created_at: '2026-07-01T08:00:00Z',
    last_used_at: null,
    expires_at: '2999-01-01T00:00:00Z',
    revoked_at: null,
  },
  {
    id: 2,
    user_id: 2,
    name: 'expired-token',
    scope: 'mcp',
    prefix: 'ab_mcp_exp',
    created_at: '2026-07-02T08:00:00Z',
    last_used_at: null,
    expires_at: '2000-01-01T00:00:00Z',
    revoked_at: null,
  },
  {
    id: 3,
    user_id: 1,
    name: 'revoked-token',
    scope: 'api',
    prefix: 'ab_api_rev',
    created_at: '2026-07-03T08:00:00Z',
    last_used_at: null,
    expires_at: null,
    revoked_at: '2026-07-04T08:00:00Z',
  },
];

const FoldPanelStub = defineComponent({
  template: '<section><slot /></section>',
});

const ButtonStub = defineComponent({
  props: {
    disabled: Boolean,
    loading: Boolean,
  },
  emits: ['click'],
  template:
    '<button :disabled="disabled || loading" @click="$emit(\'click\', $event)"><slot /></button>',
});

const ModalStub = defineComponent({
  props: {
    show: Boolean,
    title: String,
  },
  emits: ['update:show', 'after-leave'],
  template: `
    <div v-if="show" class="stub-modal" :data-title="title">
      <button class="stub-modal-close" @click="$emit('update:show', false)">close</button>
      <slot />
      <slot name="footer" />
    </div>
  `,
});

const FieldStub = defineComponent({
  template: '<label><slot /></label>',
});

const InputStub = defineComponent({
  props: {
    modelValue: { type: [String, Number], default: '' },
    type: { type: String, default: 'text' },
  },
  emits: ['update:modelValue'],
  template: `
    <input
      :type="type"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  `,
});

const SelectStub = defineComponent({
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<select :value="modelValue"><slot /></select>',
});

const SwitchStub = defineComponent({
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template:
    '<button class="stub-switch" @click="$emit(\'update:modelValue\', !modelValue)">switch</button>',
});

interface AccessSetupState {
  issuedToken: string;
  password: string;
  showTokenDialog: boolean;
  showTokenValue: boolean;
  showUserDialog: boolean;
  username: string;
}

function getAccessState(wrapper: VueWrapper): AccessSetupState {
  const component = wrapper.findComponent(ConfigAccess);
  const instance = component.vm as ComponentPublicInstance & {
    $: { setupState: AccessSetupState };
  };
  return instance.$.setupState;
}

function buttonWithText(
  wrapper: VueWrapper | DOMWrapper<Element>,
  text: string
) {
  const button = wrapper.findAll('button').find((item) => item.text() === text);
  if (!button) throw new Error(`Button not found: ${text}`);
  return button;
}

function mountAccess() {
  const active = ref(true);
  const Host = defineComponent({
    components: { ConfigAccess, KeepAlive },
    setup: () => ({ active }),
    template: `
      <KeepAlive>
        <ConfigAccess v-if="active" />
      </KeepAlive>
    `,
  });

  const wrapper = mount(Host, {
    global: {
      components: {
        AbButton: ButtonStub,
        AbField: FieldStub,
        AbFoldPanel: FoldPanelStub,
        AbInput: InputStub,
        AbModal: ModalStub,
        AbSelect: SelectStub,
        AbSwitch: SwitchStub,
      },
    },
  });
  return { active, wrapper };
}

describe('config access', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiUsers.list).mockResolvedValue(users);
    vi.mocked(apiTokens.list).mockResolvedValue(tokens);
  });

  it('reloads access state whenever its KeepAlive tree is activated', async () => {
    const { active, wrapper } = mountAccess();
    await flushPromises();
    expect(apiUsers.list).toHaveBeenCalledTimes(1);
    expect(apiTokens.list).toHaveBeenCalledTimes(1);

    active.value = false;
    await nextTick();
    active.value = true;
    await flushPromises();

    expect(apiUsers.list).toHaveBeenCalledTimes(2);
    expect(apiTokens.list).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it('renders token owners and active, expired, and revoked states', async () => {
    const { wrapper } = mountAccess();
    await flushPromises();

    expect(wrapper.text()).toContain('access.owner: alice');
    expect(wrapper.text()).toContain('access.owner: bob');
    expect(wrapper.find('.token-status--active').text()).toBe(
      'access.token_status_active'
    );
    expect(wrapper.find('.token-status--expired').text()).toBe(
      'access.token_status_expired'
    );
    expect(wrapper.find('.token-status--revoked').text()).toBe(
      'access.token_status_revoked'
    );
    expect(wrapper.text()).toContain('expired-token');
    expect(wrapper.text()).toContain('revoked-token');
    expect(wrapper.find('[role="group"][aria-label="alice"]').exists()).toBe(
      true
    );
    expect(
      wrapper.find('[role="group"][aria-label="active-token"]').exists()
    ).toBe(true);
    wrapper.unmount();
  });

  it('treats timezone-less backend token timestamps as UTC', async () => {
    vi.mocked(apiTokens.list).mockResolvedValue([
      {
        ...tokens[0],
        expires_at: '2000-01-01T00:00:00',
      },
    ]);
    const parse = vi
      .spyOn(Date, 'parse')
      .mockImplementation((value) =>
        String(value).endsWith('Z') ? 0 : Number.MAX_SAFE_INTEGER
      );

    const { wrapper } = mountAccess();
    await flushPromises();

    expect(wrapper.find('.token-status--expired').exists()).toBe(true);
    expect(parse).toHaveBeenCalledWith('2000-01-01T00:00:00Z');
    parse.mockRestore();
    wrapper.unmount();
  });

  it('scrubs password and one-time token refs when their dialogs close', async () => {
    const created: ApiTokenCreated = {
      ...tokens[0],
      id: 10,
      name: 'new-token',
      expires_at: null,
      token: 'ab_api_one_time_secret',
    };
    vi.mocked(apiTokens.create).mockResolvedValue(created);
    const { wrapper } = mountAccess();
    await flushPromises();
    const state = getAccessState(wrapper);

    await buttonWithText(wrapper, 'access.add_user').trigger('click');
    const userDialog = wrapper.find('[data-title="access.add_user"]');
    const userInputs = userDialog.findAll('input');
    await userInputs[0].setValue('charlie');
    await userInputs[1].setValue('secret-password');
    expect(state.password).toBe('secret-password');
    await buttonWithText(userDialog, 'config.cancel').trigger('click');
    await nextTick();
    expect(state.password).toBe('');
    expect(state.username).toBe('');

    await buttonWithText(wrapper, 'access.add_token').trigger('click');
    const tokenDialog = wrapper.find('[data-title="access.add_token"]');
    await tokenDialog.find('input').setValue('new-token');
    await buttonWithText(tokenDialog, 'access.create').trigger('click');
    await flushPromises();
    expect(state.issuedToken).toBe('ab_api_one_time_secret');
    wrapper
      .findAllComponents(ModalStub)
      .find((modal) => modal.props('title') === 'access.add_token')!
      .vm.$emit('after-leave');
    await nextTick();
    expect(wrapper.text()).toContain('ab_api_one_time_secret');
    expect(wrapper.find('[aria-label="access.one_time_token"]').text()).toBe(
      'ab_api_one_time_secret'
    );

    await wrapper
      .find('[data-title="access.token_created"] .stub-modal-close')
      .trigger('click');
    await nextTick();
    expect(state.issuedToken).toBe('');
    wrapper.unmount();
  });

  it('reveals a created token only after the create dialog finishes leaving', async () => {
    vi.mocked(apiTokens.create).mockResolvedValue({
      ...tokens[0],
      id: 11,
      name: 'queued-token',
      expires_at: null,
      token: 'ab_api_queued_one_time_secret',
    });
    const { wrapper } = mountAccess();
    await flushPromises();
    const state = getAccessState(wrapper);

    await buttonWithText(wrapper, 'access.add_token').trigger('click');
    const tokenDialog = wrapper.find('[data-title="access.add_token"]');
    await tokenDialog.find('input').setValue('queued-token');
    await buttonWithText(tokenDialog, 'access.create').trigger('click');
    await flushPromises();
    const beforeLeave = state.showTokenValue;
    wrapper
      .findAllComponents(ModalStub)
      .find((modal) => modal.props('title') === 'access.add_token')!
      .vm.$emit('after-leave');
    await nextTick();

    expect({ beforeLeave, afterLeave: state.showTokenValue }).toEqual({
      beforeLeave: false,
      afterLeave: true,
    });
    wrapper.unmount();
  });

  it('scrubs sensitive refs on deactivation and before unmount', async () => {
    const { active, wrapper } = mountAccess();
    await flushPromises();
    const state = getAccessState(wrapper);

    state.password = 'deactivate-password';
    state.issuedToken = 'deactivate-token';
    state.showUserDialog = true;
    state.showTokenValue = true;
    active.value = false;
    await nextTick();

    expect(state.password).toBe('');
    expect(state.issuedToken).toBe('');
    expect(state.showUserDialog).toBe(false);
    expect(state.showTokenValue).toBe(false);

    active.value = true;
    await flushPromises();
    state.password = 'unmount-password';
    state.issuedToken = 'unmount-token';
    wrapper.unmount();

    expect(state.password).toBe('');
    expect(state.issuedToken).toBe('');
  });

  it('does not restore a one-time token when creation resolves after deactivation', async () => {
    let resolveCreate!: (token: ApiTokenCreated) => void;
    vi.mocked(apiTokens.create).mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = resolve;
      })
    );
    const { active, wrapper } = mountAccess();
    await flushPromises();
    const state = getAccessState(wrapper);

    await buttonWithText(wrapper, 'access.add_token').trigger('click');
    const tokenDialog = wrapper.find('[data-title="access.add_token"]');
    await tokenDialog.find('input').setValue('late-token');
    await buttonWithText(tokenDialog, 'access.create').trigger('click');

    active.value = false;
    await nextTick();
    resolveCreate({
      ...tokens[0],
      id: 20,
      name: 'late-token',
      token: 'ab_api_late_one_time_secret',
    });
    await flushPromises();

    expect(state.issuedToken).toBe('');
    expect(state.showTokenValue).toBe(false);

    active.value = true;
    await flushPromises();
    expect(wrapper.text()).not.toContain('ab_api_late_one_time_secret');
    wrapper.unmount();
  });
});
