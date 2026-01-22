import type { ApiSuccess } from '#/api';
import type { LoginSuccess } from '#/auth';
import type {
  AuthenticationOptions,
  PasskeyAuthFinishRequest,
  PasskeyAuthStartRequest,
  PasskeyCreateRequest,
  PasskeyDeleteRequest,
  PasskeyItem,
  RegistrationOptions,
} from '#/passkey';

/**
 * Passkey API 客户端
 */
export const apiPasskey = {
  // ============ 注册流程 ============

  /**
   * 获取注册选项（步骤 1）
   */
  async getRegistrationOptions(): Promise<RegistrationOptions> {
    const { data } = await axios.post<RegistrationOptions>(
      'api/v1/passkey/register/options'
    );
    return data;
  },

  /**
   * 提交注册结果（步骤 2）
   */
  async verifyRegistration(request: PasskeyCreateRequest): Promise<ApiSuccess> {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/passkey/register/verify',
      request
    );
    return data;
  },

  // ============ 认证流程 ============

  /**
   * 获取登录选项（步骤 1）
   */
  async getLoginOptions(
    request: PasskeyAuthStartRequest
  ): Promise<AuthenticationOptions> {
    const { data } = await axios.post<AuthenticationOptions>(
      'api/v1/passkey/auth/options',
      request
    );
    return data;
  },

  /**
   * 提交认证结果（步骤 2）
   */
  async loginWithPasskey(
    request: PasskeyAuthFinishRequest
  ): Promise<LoginSuccess> {
    const { data } = await axios.post<LoginSuccess>(
      'api/v1/passkey/auth/verify',
      request
    );
    return data;
  },

  // ============ 管理 ============

  /**
   * 获取 Passkey 列表
   */
  async list(): Promise<PasskeyItem[]> {
    const { data } = await axios.get<PasskeyItem[]>('api/v1/passkey/list');
    return data;
  },

  /**
   * 删除 Passkey
   */
  async delete(request: PasskeyDeleteRequest): Promise<ApiSuccess> {
    const { data } = await axios.post<ApiSuccess>(
      'api/v1/passkey/delete',
      request
    );
    return data;
  },
};
