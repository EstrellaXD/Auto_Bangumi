/**
 * Tests for useApi hook logic
 * Note: These tests focus on testable aspects of the hook's behavior
 */

import { describe, it, expect, vi } from 'vitest';

// Simplified useApi implementation for testing
interface Options<T = unknown> {
  showMessage?: boolean;
  onBeforeExecute?: () => void;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
  onFinally?: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyAsyncFunction = (...args: any[]) => Promise<any>;

function createUseApi<TApi extends AnyAsyncFunction>(
  api: TApi,
  options: Options<Awaited<ReturnType<TApi>>> = {}
) {
  let data: Awaited<ReturnType<TApi>> | undefined;
  let isLoading = false;

  const execute = async (...params: Parameters<TApi>): Promise<void> => {
    options.onBeforeExecute?.();
    isLoading = true;
    try {
      const res: Awaited<ReturnType<TApi>> = await api(...params);
      data = res;
      options.onSuccess?.(res);
    } catch (err) {
      options.onError?.(err);
    } finally {
      isLoading = false;
      options.onFinally?.();
    }
  };

  return {
    getData: () => data,
    getIsLoading: () => isLoading,
    execute,
  };
}

describe('useApi logic', () => {
  describe('execute', () => {
    it('should call API function with provided parameters', async () => {
      const mockApi = vi.fn().mockResolvedValue({ msg_en: 'Success' });
      const { execute } = createUseApi(mockApi);

      await execute('param1', 'param2', 123);

      expect(mockApi).toHaveBeenCalledWith('param1', 'param2', 123);
    });

    it('should set data to API response on success', async () => {
      const responseData = { msg_en: 'Success', value: 42 };
      const mockApi = vi.fn().mockResolvedValue(responseData);
      const { execute, getData } = createUseApi(mockApi);

      await execute();

      expect(getData()).toEqual(responseData);
    });
  });

  describe('callbacks', () => {
    it('should call onBeforeExecute before API call', async () => {
      const onBeforeExecute = vi.fn();
      const mockApi = vi.fn().mockResolvedValue({});
      const { execute } = createUseApi(mockApi, { onBeforeExecute });

      await execute();

      expect(onBeforeExecute).toHaveBeenCalled();
    });

    it('should call onSuccess with response data', async () => {
      const onSuccess = vi.fn();
      const responseData = { msg_en: 'Success', id: 1 };
      const mockApi = vi.fn().mockResolvedValue(responseData);
      const { execute } = createUseApi(mockApi, { onSuccess });

      await execute();

      expect(onSuccess).toHaveBeenCalledWith(responseData);
    });

    it('should call onError when API throws', async () => {
      const onError = vi.fn();
      const error = new Error('API Error');
      const mockApi = vi.fn().mockRejectedValue(error);
      const { execute } = createUseApi(mockApi, { onError });

      await execute();

      expect(onError).toHaveBeenCalledWith(error);
    });

    it('should call onFinally after success', async () => {
      const onFinally = vi.fn();
      const mockApi = vi.fn().mockResolvedValue({});
      const { execute } = createUseApi(mockApi, { onFinally });

      await execute();

      expect(onFinally).toHaveBeenCalled();
    });

    it('should call onFinally after error', async () => {
      const onFinally = vi.fn();
      const mockApi = vi.fn().mockRejectedValue(new Error());
      const { execute } = createUseApi(mockApi, { onFinally, onError: vi.fn() });

      await execute();

      expect(onFinally).toHaveBeenCalled();
    });
  });

  describe('error handling', () => {
    it('should set isLoading to false after error', async () => {
      const mockApi = vi.fn().mockRejectedValue(new Error('API Error'));
      const { execute, getIsLoading } = createUseApi(mockApi, { onError: vi.fn() });

      await execute();

      expect(getIsLoading()).toBe(false);
    });

    it('should not set data on error', async () => {
      const mockApi = vi.fn().mockRejectedValue(new Error('API Error'));
      const { execute, getData } = createUseApi(mockApi, { onError: vi.fn() });

      await execute();

      expect(getData()).toBeUndefined();
    });
  });
});
