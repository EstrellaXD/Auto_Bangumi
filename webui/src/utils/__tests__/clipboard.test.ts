import { afterEach, describe, expect, it, vi } from 'vitest';
import { copyText } from '../clipboard';

function setSecureContext(secure: boolean) {
  Object.defineProperty(window, 'isSecureContext', {
    value: secure,
    configurable: true,
  });
}

describe('copyText', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should use navigator.clipboard when the context is secure', async () => {
    setSecureContext(true);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    expect(await copyText('token')).toBe(true);
    expect(writeText).toHaveBeenCalledWith('token');
  });

  it.each([true, false])(
    'should return the execCommand result %s when the context is not secure',
    async (result) => {
      setSecureContext(false);
      const execCommand = vi.fn().mockReturnValue(result);
      Object.defineProperty(document, 'execCommand', {
        value: execCommand,
        configurable: true,
      });

      expect(await copyText('token')).toBe(result);
      expect(execCommand).toHaveBeenCalledWith('copy');
      expect(document.querySelector('textarea')).toBeNull();
    }
  );
});
