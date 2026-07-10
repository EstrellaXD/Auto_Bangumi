import { test as base, expect } from '@playwright/test';
import { E2EApi } from './api';
import type { E2EEnvironment } from './env';
import { getE2EEnvironment } from './env';
import { NetworkGuard } from './network';

interface E2EFixtures {
  environment: E2EEnvironment;
  api: E2EApi;
  uniqueName: string;
  diagnostics: void;
}

export const test = base.extend<E2EFixtures>({
  environment: async ({ browserName: _browserName }, use) => {
    await use(getE2EEnvironment());
  },
  api: async ({ request }, use) => {
    await use(new E2EApi(request));
  },
  uniqueName: async ({ browserName: _browserName }, use, testInfo) => {
    const value = `${testInfo.project.name}-${testInfo.testId}`
      .replace(/[^A-Za-z0-9_-]+/g, '-')
      .slice(-48);
    await use(value);
  },
  diagnostics: [
    async ({ page, environment }, use, testInfo) => {
      const guard = new NetworkGuard(page, environment);
      await guard.install();
      await use();
      await guard.finish(testInfo);
    },
    { auto: true },
  ],
});

export { expect };
