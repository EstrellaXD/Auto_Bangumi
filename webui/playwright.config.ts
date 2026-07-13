import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

const profile = process.env.AB_E2E_PROFILE ?? 'browser';
const baseURL = process.env.AB_E2E_BASE_URL ?? 'http://127.0.0.1:0';
const projectDirectory = fileURLToPath(new URL('.', import.meta.url));
const authDirectory = resolve(projectDirectory, 'e2e/.auth');
function authFile(browser: string) {
  return resolve(authDirectory, `${profile}-${browser}.json`);
}
const downloaderOnly = profile === 'downloader';

const commonUse = {
  baseURL,
  locale: 'en-US',
  serviceWorkers: 'block' as const,
  // Raw Playwright traces serialize storage state, request bodies, and
  // response payloads.  Authenticated E2E traces would therefore publish
  // session cookies and one-time tokens with CI artifacts.  The redacted
  // NetworkGuard diagnostics below remain the supported failure record.
  trace: 'off' as const,
  screenshot: 'only-on-failure' as const,
  video: 'retain-on-failure' as const,
};

export default defineConfig({
  testDir: './e2e',
  outputDir: 'test-results',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  forbidOnly: Boolean(process.env.CI),
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: commonUse,
  projects: [
    {
      name: 'setup-chromium',
      testMatch: /setup\/bootstrap-chromium\.setup\.ts/,
      use: { ...devices['Desktop Chrome'], ...commonUse },
    },
    {
      name: 'chromium-desktop',
      testMatch: /specs\/.*\.spec\.ts/,
      dependencies: ['setup-chromium'],
      grep: downloaderOnly ? /@downloader/ : undefined,
      grepInvert: downloaderOnly ? undefined : /@(?:downloader|mobile)/,
      use: {
        ...devices['Desktop Chrome'],
        ...commonUse,
        storageState: authFile('chromium'),
      },
    },
    {
      name: 'setup-webkit',
      testMatch: /setup\/bootstrap-webkit\.setup\.ts/,
      use: {
        ...devices['iPhone 13'],
        ...commonUse,
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: 'webkit-mobile',
      testMatch: /specs\/.*\.spec\.ts/,
      dependencies: ['setup-webkit'],
      grepInvert: /@downloader/,
      use: {
        ...devices['iPhone 13'],
        ...commonUse,
        viewport: { width: 390, height: 844 },
        storageState: authFile('webkit'),
      },
    },
    {
      name: 'setup-firefox',
      testMatch: /setup\/bootstrap-firefox\.setup\.ts/,
      use: { ...devices['Desktop Firefox'], ...commonUse },
    },
    {
      name: 'firefox-nightly',
      testMatch: /specs\/.*\.spec\.ts/,
      dependencies: ['setup-firefox'],
      grepInvert: /@(?:downloader|mobile)/,
      use: {
        ...devices['Desktop Firefox'],
        ...commonUse,
        storageState: authFile('firefox'),
      },
    },
  ],
});
