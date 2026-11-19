import type { APIRequestContext, APIResponse } from '@playwright/test';
import type {
  ApiTokenCreated,
  ApiTokenPublic,
  Credentials,
  SetupStatus,
  TokenScope,
  UserPublic,
} from './data';
import { SESSION_SUCCESS } from './data';

async function requireStatus(
  response: APIResponse,
  expected: number
): Promise<APIResponse> {
  if (response.status() !== expected) {
    throw new Error(
      `${response.url()} returned ${response.status()} ` +
        `${response.statusText()}, expected ${expected}`
    );
  }
  return response;
}

export class E2EApi {
  constructor(readonly request: APIRequestContext) {}

  async setupStatus(): Promise<SetupStatus> {
    const response = await requireStatus(
      await this.request.get('/api/v1/setup/status'),
      200
    );
    return response.json();
  }

  async attemptLogin(credentials: Credentials): Promise<APIResponse> {
    return this.request.post('/api/v1/auth/login', {
      form: {
        username: credentials.username,
        password: credentials.password,
      },
    });
  }

  async login(credentials: Credentials): Promise<void> {
    const response = await requireStatus(
      await this.attemptLogin(credentials),
      200
    );
    const payload = await response.json();
    if (JSON.stringify(payload) !== JSON.stringify(SESSION_SUCCESS))
      throw new Error('Login response did not match the session-only contract');
  }

  async me(expectedStatus = 200): Promise<UserPublic | null> {
    const response = await requireStatus(
      await this.request.get('/api/v1/auth/me'),
      expectedStatus
    );
    return expectedStatus === 200 ? response.json() : null;
  }

  async logout(): Promise<void> {
    await requireStatus(await this.request.post('/api/v1/auth/logout'), 200);
  }

  async updateCurrent(credentials: Credentials): Promise<void> {
    const response = await requireStatus(
      await this.request.post('/api/v1/auth/update', {
        data: credentials,
      }),
      200
    );
    const payload = await response.json();
    if (JSON.stringify(payload) !== JSON.stringify(SESSION_SUCCESS))
      throw new Error('Credential update exposed an unexpected response shape');
  }

  async listUsers(): Promise<UserPublic[]> {
    const response = await requireStatus(
      await this.request.get('/api/v1/users'),
      200
    );
    return response.json();
  }

  async createUser(credentials: Credentials): Promise<UserPublic> {
    const response = await requireStatus(
      await this.request.post('/api/v1/users', {
        data: { ...credentials, enabled: true },
      }),
      201
    );
    return response.json();
  }

  async deleteUser(userId: number): Promise<void> {
    await requireStatus(
      await this.request.delete(`/api/v1/users/${userId}`),
      204
    );
  }

  async createToken(name: string, scope: TokenScope): Promise<ApiTokenCreated> {
    const response = await requireStatus(
      await this.request.post('/api/v1/tokens', {
        data: { name, scope },
      }),
      201
    );
    return response.json();
  }

  async listTokens(): Promise<ApiTokenPublic[]> {
    const response = await requireStatus(
      await this.request.get('/api/v1/tokens'),
      200
    );
    return response.json();
  }

  async revokeToken(tokenId: number): Promise<void> {
    await requireStatus(
      await this.request.delete(`/api/v1/tokens/${tokenId}`),
      204
    );
  }

  async bearerGet(
    path: string,
    token: string,
    expectedStatus: number
  ): Promise<APIResponse> {
    return requireStatus(
      await this.request.get(path, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      expectedStatus
    );
  }

  async disableMcpIpBypass(): Promise<void> {
    const getResponse = await requireStatus(
      await this.request.get('/api/v1/config/get'),
      200
    );
    const config = (await getResponse.json()) as Record<string, unknown> & {
      security: Record<string, unknown>;
    };
    config.security.mcp_whitelist = [];
    await requireStatus(
      await this.request.patch('/api/v1/config/update', { data: config }),
      200
    );
  }
}
