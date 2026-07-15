/* eslint-disable vue/one-component-per-file */
import { readFileSync } from 'node:fs';
import { defineComponent } from 'vue';
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LlmAuthDialog from '../llm-auth-dialog.vue';
import { apiLLM } from '@/api/llm';
import type { LLMAuthChallenge } from '@/api/llm';

const message = {
  error: vi.fn(),
  success: vi.fn(),
};

vi.mock('@/api/llm', () => ({
  apiLLM: {
    beginAuth: vi.fn(),
    completeAuth: vi.fn(),
    getAuthStatus: vi.fn(),
  },
}));
vi.mock('@/hooks/useMessage', () => ({ useMessage: () => message }));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

const redirectChallenge: LLMAuthChallenge = {
  method: 'redirect_paste',
  authorize_url: 'https://example.test/authorize',
  user_code: null,
  verification_uri: null,
  expires_in: 600,
  state: 'oauth-state',
};

const deviceChallenge: LLMAuthChallenge = {
  method: 'device_code',
  authorize_url: null,
  user_code: 'ABCD-EFGH',
  verification_uri: 'https://example.test/device',
  expires_in: 600,
  state: 'device-state',
};

const AdaptiveModalStub = defineComponent({
  name: 'AbModal',
  props: {
    desktopMaxWidth: String,
    show: Boolean,
    size: String,
    title: String,
  },
  emits: ['update:show'],
  template: `
    <section
      data-ab-modal
      :data-desktop-max-width="desktopMaxWidth"
      :data-show="show"
      :data-size="size"
    >
      <h2>{{ title }}</h2>
      <slot />
      <button type="button" data-modal-close @click="$emit('update:show', false)">
        close
      </button>
    </section>
  `,
});

const NaiveModalStub = defineComponent({
  name: 'NModal',
  props: {
    show: Boolean,
    title: String,
  },
  emits: ['update:show'],
  template: `
    <section data-naive-modal :data-show="show">
      <h2>{{ title }}</h2>
      <slot />
      <button type="button" data-modal-close @click="$emit('update:show', false)">
        close
      </button>
    </section>
  `,
});

const InputStub = defineComponent({
  name: 'NInput',
  props: {
    value: String,
  },
  emits: ['update:value'],
  template: `
    <textarea
      data-auth-code-input
      :value="value"
      @input="$emit('update:value', $event.target.value)"
    />
  `,
});

const ButtonStub = defineComponent({
  name: 'AbButton',
  props: {
    disabled: Boolean,
    loading: Boolean,
  },
  emits: ['click'],
  template: `
    <button
      type="button"
      data-connect
      :disabled="disabled || loading"
      @click="$emit('click', $event)"
    ><slot /></button>
  `,
});

enableAutoUnmount(afterEach);

function mountDialog() {
  return mount(LlmAuthDialog, {
    props: {
      show: false,
      providerId: 'openai-codex',
      displayName: 'OpenAI Codex',
    },
    global: {
      stubs: {
        AbButton: ButtonStub,
        AbModal: AdaptiveModalStub,
        Input: InputStub,
        Modal: NaiveModalStub,
        NInput: InputStub,
        NModal: NaiveModalStub,
      },
    },
  });
}

async function openRedirectDialog() {
  vi.mocked(apiLLM.beginAuth).mockResolvedValue(redirectChallenge);
  const wrapper = mountDialog();
  await wrapper.setProps({ show: true });
  await flushPromises();
  return wrapper;
}

describe('llm-auth-dialog adaptive modal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    vi.mocked(apiLLM.beginAuth).mockResolvedValue(redirectChallenge);
    vi.mocked(apiLLM.completeAuth).mockResolvedValue({
      connected: true,
      account_label: 'codex@example.test',
    });
    vi.mocked(apiLLM.getAuthStatus).mockResolvedValue({
      connected: false,
      account_label: '',
      expires_at: null,
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('should use the adaptive modal shell', () => {
    const wrapper = mountDialog();

    expect(wrapper.find('[data-ab-modal]').exists()).toBe(true);
  });

  it('should preserve the previous desktop dialog width', () => {
    const wrapper = mountDialog();

    expect(
      wrapper.get('[data-ab-modal]').attributes('data-desktop-max-width')
    ).toBe('460px');
  });

  it('should begin the provider connection when v-model opens', async () => {
    const wrapper = mountDialog();

    await wrapper.setProps({ show: true });
    await flushPromises();

    expect(apiLLM.beginAuth).toHaveBeenCalledWith('openai-codex');
  });

  it('should emit v-model close when the modal requests dismissal', async () => {
    const wrapper = await openRedirectDialog();

    await wrapper.get('[data-modal-close]').trigger('click');

    expect(wrapper.emitted('update:show')).toEqual([[false]]);
  });

  it('should reset pasted authorization code after modal dismissal', async () => {
    const wrapper = await openRedirectDialog();
    await wrapper.get('[data-auth-code-input]').setValue('temporary-code');

    await wrapper.get('[data-modal-close]').trigger('click');
    await wrapper.setProps({ show: false });
    await wrapper.setProps({ show: true });
    await flushPromises();

    expect(
      wrapper.get<HTMLTextAreaElement>('[data-auth-code-input]').element.value
    ).toBe('');
  });

  it('should stop device polling when the modal requests dismissal', async () => {
    vi.mocked(apiLLM.beginAuth).mockResolvedValue(deviceChallenge);
    const wrapper = mountDialog();
    await wrapper.setProps({ show: true });
    await flushPromises();
    await vi.advanceTimersByTimeAsync(3000);

    await wrapper.get('[data-modal-close]').trigger('click');
    await vi.advanceTimersByTimeAsync(6000);

    expect(apiLLM.getAuthStatus).toHaveBeenCalledTimes(1);
  });

  it('should submit the trimmed code with the active challenge state', async () => {
    const wrapper = await openRedirectDialog();
    await wrapper.get('[data-auth-code-input]').setValue('  pasted-code  ');

    await wrapper.get('[data-connect]').trigger('click');
    await flushPromises();

    expect(apiLLM.completeAuth).toHaveBeenCalledWith('openai-codex', {
      state: 'oauth-state',
      code: 'pasted-code',
    });
  });

  it('should emit connected after authorization completes', async () => {
    const wrapper = await openRedirectDialog();
    await wrapper.get('[data-auth-code-input]').setValue('pasted-code');

    await wrapper.get('[data-connect]').trigger('click');
    await flushPromises();

    expect(wrapper.emitted('connected')).toHaveLength(1);
  });

  it('should give the mobile textarea a phone-sized touch target', () => {
    const source = readFileSync(
      new URL('../llm-auth-dialog.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.auth-code-input\s*\{[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });

  it('should give the mobile connect action a phone-sized touch target', () => {
    const source = readFileSync(
      new URL('../llm-auth-dialog.vue', import.meta.url),
      'utf8'
    );

    expect(source).toMatch(
      /@media screen and \(max-width: 639px\)[\s\S]*?\.auth-submit\s*\{[\s\S]*?min-height:\s*var\(--touch-target\)/
    );
  });
});
