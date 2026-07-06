export type LLMAuthKind = 'api_key' | 'oauth' | 'device_code';

export interface LLMProviderView {
  id: string;
  display_name: string;
  auth_kind: LLMAuthKind;
  builtin: boolean;
  needs_base_url: boolean;
  preset_base_url: string;
  default_model: string;
  plugin_version: string | null;
  connected: boolean;
  account_label: string;
  expires_at: number | null;
}

export interface LLMAuthChallenge {
  method: 'redirect_paste' | 'device_code';
  authorize_url: string | null;
  user_code: string | null;
  verification_uri: string | null;
  expires_in: number;
  state: string;
}

export interface LLMAuthStatus {
  connected: boolean;
  account_label: string;
  expires_at: number | null;
}

export const apiLLM = {
  async getProviders() {
    const { data } = await axios.get<{ providers: LLMProviderView[] }>(
      'api/v1/config/llm/providers',
      { silent: true }
    );
    return data!.providers;
  },

  async installProvider(id: string) {
    const { data } = await axios.post<{ success: boolean; version: string }>(
      `api/v1/config/llm/providers/${id}/install`
    );
    return data!;
  },

  async uninstallProvider(id: string) {
    await axios.delete(`api/v1/config/llm/providers/${id}`);
  },

  async beginAuth(id: string) {
    const { data } = await axios.post<LLMAuthChallenge>(
      `api/v1/config/llm/providers/${id}/auth/begin`
    );
    return data!;
  },

  async completeAuth(id: string, payload: { state: string; code?: string }) {
    const { data } = await axios.post<{
      connected: boolean;
      account_label: string;
    }>(`api/v1/config/llm/providers/${id}/auth/complete`, payload);
    return data!;
  },

  async getAuthStatus(id: string) {
    const { data } = await axios.get<LLMAuthStatus>(
      `api/v1/config/llm/providers/${id}/auth/status`,
      { silent: true }
    );
    return data!;
  },

  async disconnect(id: string) {
    await axios.delete(`api/v1/config/llm/providers/${id}/auth`);
  },
};
