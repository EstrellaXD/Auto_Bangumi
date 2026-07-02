/**
 * Contract tests for apiPasskey: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/passkey.py fails a test instead of going
 * unnoticed.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockLoginSuccess } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';
import type {
  PasskeyAuthFinishRequest,
  PasskeyAuthStartRequest,
  PasskeyCreateRequest,
  PasskeyDeleteRequest,
} from '#/passkey';

import { apiPasskey } from '@/api/passkey';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Passkey API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should POST api/v1/passkey/register/options when starting registration', async () => {
    (axios.post as any).mockResolvedValue({
      data: { challenge: 'c', rp: { name: 'AB', id: 'localhost' }, user: {}, pubKeyCredParams: [] },
    });
    await apiPasskey.getRegistrationOptions();
    expect(axios.post).toHaveBeenCalledWith('api/v1/passkey/register/options');
  });

  it('should POST api/v1/passkey/register/verify with the credential when finishing registration', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    const request: PasskeyCreateRequest = { name: 'my device', attestation_response: {} };
    await apiPasskey.verifyRegistration(request);
    expect(axios.post).toHaveBeenCalledWith('api/v1/passkey/register/verify', request);
  });

  it('should POST api/v1/passkey/auth/options with the username when starting login', async () => {
    (axios.post as any).mockResolvedValue({ data: { challenge: 'c' } });
    const request: PasskeyAuthStartRequest = { username: 'admin' };
    await apiPasskey.getLoginOptions(request);
    expect(axios.post).toHaveBeenCalledWith('api/v1/passkey/auth/options', request);
  });

  it('should POST api/v1/passkey/auth/verify with the credential when finishing login', async () => {
    (axios.post as any).mockResolvedValue({ data: mockLoginSuccess });
    const request: PasskeyAuthFinishRequest = { username: 'admin', credential: {} };
    await apiPasskey.loginWithPasskey(request);
    expect(axios.post).toHaveBeenCalledWith('api/v1/passkey/auth/verify', request);
  });

  it('should GET api/v1/passkey/list when listing passkeys', async () => {
    (axios.get as any).mockResolvedValue({ data: [] });
    await apiPasskey.list();
    expect(axios.get).toHaveBeenCalledWith('api/v1/passkey/list');
  });

  it('should POST api/v1/passkey/delete with the passkey id when deleting', async () => {
    (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
    const request: PasskeyDeleteRequest = { passkey_id: 1 };
    await apiPasskey.delete(request);
    expect(axios.post).toHaveBeenCalledWith('api/v1/passkey/delete', request);
  });
});
