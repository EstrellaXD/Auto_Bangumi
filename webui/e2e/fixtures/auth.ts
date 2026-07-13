import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import type {
  Browser,
  BrowserContext,
  Page,
  Response,
  TestInfo,
} from '@playwright/test';
import { expect } from '@playwright/test';
import { E2EApi } from './api';
import type { Credentials } from './data';
import { SESSION_SUCCESS } from './data';
import type { E2EEnvironment } from './env';
import { NetworkGuard } from './network';

export async function forceEnglish(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem('lang', 'en'));
}

export async function loginThroughUI(
  page: Page,
  credentials: Credentials,
  expectedStatus = 200
): Promise<Response> {
  await page.goto('/#/login');
  await page.getByLabel('Username').fill(credentials.username);
  await page.getByLabel('Password').fill(credentials.password);
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/login') &&
      response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(expectedStatus);
  if (expectedStatus === 200) {
    expect(await response.json()).toEqual(SESSION_SUCCESS);
    await expect(page).toHaveURL(/#\/bangumi$/);
  }
  return response;
}

export async function completeFirstRunSetup(
  page: Page,
  environment: E2EEnvironment
): Promise<void> {
  await forceEnglish(page);
  await page.goto('/#/setup');
  await expect(page.getByRole('progressbar')).toHaveAttribute(
    'aria-valuenow',
    '1'
  );
  await page.getByRole('button', { name: 'Get Started' }).click();

  await page.getByLabel('Username').fill(environment.username);
  await page.getByLabel('Password', { exact: true }).fill(environment.password);
  await page.getByLabel('Confirm Password').fill(environment.password);
  await page.getByRole('button', { name: 'Next' }).click();

  await page.getByLabel('Host').fill(environment.downloaderURL);
  await page.getByLabel('Username').fill(environment.downloaderUsername);
  await page.getByLabel('Password').fill(environment.downloaderPassword);
  await page.getByLabel('Download Path').fill('/downloads/Bangumi');
  await page.getByRole('button', { name: 'Next' }).click();

  await page.getByRole('button', { name: 'Skip' }).click();
  await page.getByRole('button', { name: 'Skip' }).click();

  const completeResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/setup/complete') &&
      response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Complete Setup' }).click();
  const response = await completeResponse;
  expect(response.status()).toBe(200);
  expect(await response.json()).toMatchObject({ status: true });
  await expect(page).toHaveURL(/#\/login$/);
}

export async function bootstrapAuthenticatedState(
  page: Page,
  environment: E2EEnvironment,
  storageStatePath: string
): Promise<void> {
  const api = new E2EApi(page.context().request);
  const setup = await api.setupStatus();
  if (setup.need_setup) await completeFirstRunSetup(page, environment);
  await loginThroughUI(page, environment);

  const tokenCookie = (await page.context().cookies()).find(
    (cookie) => cookie.name === 'token'
  );
  expect(tokenCookie).toMatchObject({ httpOnly: true, sameSite: 'Strict' });

  await api.disableMcpIpBypass();
  await mkdir(dirname(storageStatePath), { recursive: true });
  await page.context().storageState({ path: storageStatePath });
}

export interface AuthenticatedContext {
  context: BrowserContext;
  page: Page;
  guard: NetworkGuard;
}

export async function closeAuthenticatedContexts(
  contexts: AuthenticatedContext[],
  testInfo: TestInfo
): Promise<void> {
  const guardResults = await Promise.allSettled(
    contexts.map(({ guard }) => guard.finish(testInfo))
  );
  const closeResults = await Promise.allSettled(
    contexts.map(({ context }) => context.close())
  );
  const failure = [...guardResults, ...closeResults].find(
    (result): result is PromiseRejectedResult => result.status === 'rejected'
  );
  if (failure) throw failure.reason;
}

export async function newAuthenticatedContext(
  browser: Browser,
  environment: E2EEnvironment,
  credentials: Credentials,
  testInfo: TestInfo
): Promise<AuthenticatedContext> {
  const mobile = testInfo.project.name.includes('webkit');
  const context = await browser.newContext({
    baseURL: environment.baseURL,
    locale: 'en-US',
    serviceWorkers: 'block',
    // The Playwright `browser` fixture applies the project's authenticated
    // storage state to manually-created contexts unless it is overridden.
    // Secondary-user and logout tests need a genuinely empty session.
    storageState: { cookies: [], origins: [] },
    viewport: mobile
      ? { width: 390, height: 844 }
      : { width: 1280, height: 720 },
  });
  try {
    const page = await context.newPage();
    await forceEnglish(page);
    const guard = new NetworkGuard(page, environment);
    await guard.install();
    await loginThroughUI(page, credentials);
    return { context, page, guard };
  } catch (error) {
    await context.close().catch(() => undefined);
    throw error;
  }
}
