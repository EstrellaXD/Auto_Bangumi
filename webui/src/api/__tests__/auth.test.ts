/**
 * Tests for Auth API logic
 * Note: These tests focus on the data structures and transformations
 */

import { describe, expect, it, vi } from 'vitest';
import { mockApiSuccess, mockLoginSuccess } from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiAuth } from '@/api/auth';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Auth API Data Structures', () => {
  describe('login response', () => {
    it('should have access_token and token_type', () => {
      expect(mockLoginSuccess.access_token).toBeDefined();
      expect(mockLoginSuccess.token_type).toBe('bearer');
    });

    it('should have string access_token', () => {
      expect(typeof mockLoginSuccess.access_token).toBe('string');
      expect(mockLoginSuccess.access_token.length).toBeGreaterThan(0);
    });
  });

  describe('login request formation', () => {
    it('should create URLSearchParams with username and password', () => {
      const username = 'testuser';
      const password = 'testpassword';

      const formData = new URLSearchParams({
        username,
        password,
      });

      expect(formData.toString()).toContain('username=testuser');
      expect(formData.toString()).toContain('password=testpassword');
    });

    it('should properly encode special characters in credentials', () => {
      const username = 'test@user.com';
      const password = 'pass&word=123';

      const formData = new URLSearchParams({
        username,
        password,
      });

      expect(formData.get('username')).toBe('test@user.com');
      expect(formData.get('password')).toBe('pass&word=123');
    });
  });

  describe('update request formation', () => {
    it('should create update payload with username and password', () => {
      const username = 'newuser';
      const password = 'newpassword123';

      const payload = {
        username,
        password,
      };

      expect(payload.username).toBe('newuser');
      expect(payload.password).toBe('newpassword123');
    });
  });

  // Contract tests: call the real apiAuth functions against a mocked axios
  // instance so a drift between the wrapper and the FastAPI routes in
  // backend/src/module/api/auth.py fails a test instead of going unnoticed.
  describe('API contract (path + HTTP method)', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should POST api/v1/auth/login with form-encoded credentials when logging in', async () => {
      (axios.post as any).mockResolvedValue({ data: mockLoginSuccess });
      await apiAuth.login('testuser', 'testpassword');

      expect(axios.post).toHaveBeenCalledTimes(1);
      const [url, body, config] = (axios.post as any).mock.calls[0];
      expect(url).toBe('api/v1/auth/login');
      expect(body).toBeInstanceOf(URLSearchParams);
      expect((body as URLSearchParams).get('username')).toBe('testuser');
      expect((body as URLSearchParams).get('password')).toBe('testpassword');
      expect(config.headers['Content-Type']).toBe(
        'application/x-www-form-urlencoded'
      );
    });

    it('should POST api/v1/auth/refresh_token when refreshing the session', async () => {
      (axios.post as any).mockResolvedValue({ data: mockLoginSuccess });
      await apiAuth.refresh();
      // silent: an expired-session refresh at startup must not toast; the 401
      // handler still logs out and routes to /login.
      expect(axios.post).toHaveBeenCalledWith(
        'api/v1/auth/refresh_token',
        undefined,
        { silent: true }
      );
    });

    it('should POST api/v1/auth/logout when logging out', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiAuth.logout();
      expect(axios.post).toHaveBeenCalledWith('api/v1/auth/logout');
    });

    it('should POST api/v1/auth/update with the new credentials when updating', async () => {
      (axios.post as any).mockResolvedValue({
        ...mockLoginSuccess,
        message: 'update success',
      });
      await apiAuth.update('newuser', 'newpassword123');
      expect(axios.post).toHaveBeenCalledWith('api/v1/auth/update', {
        username: 'newuser',
        password: 'newpassword123',
      });
    });
  });
});
