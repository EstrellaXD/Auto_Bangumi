/**
 * Shared axios mock factory for API contract tests.
 *
 * `src/utils/axios.ts` builds its exported `axios` instance eagerly at
 * module scope and pulls in `useAuth`/the router along the way, so it can't
 * be imported directly under vitest. Contract tests instead
 * `vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }))` to swap
 * in this lightweight double before the real module (and its router chain)
 * ever loads.
 */
import { vi } from 'vitest';

export function createAxiosMock() {
  return {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
  };
}
