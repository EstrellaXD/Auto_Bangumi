import type { Locator, Page } from '@playwright/test';
import { expect, test } from '../fixtures/test';

const MOBILE_VIEWPORT = { width: 390, height: 844 };
const SHORT_VIEWPORT = { width: 390, height: 360 };
const SETUP_DRAFT_KEY = 'ab-setup-wizard';

interface SetupDraft {
  currentStepIndex: number;
  accountData: {
    username: string;
    password: string;
    confirmPassword: string;
  };
  downloaderData: {
    type: 'qbittorrent';
    host: string;
    username: string;
    password: string;
    path: string;
    ssl: boolean;
  };
  rssData: { url: string; name: string; skipped: boolean };
  notificationData: {
    enable: boolean;
    type: 'telegram';
    token: string;
    chat_id: string;
    skipped: boolean;
  };
  validation: {
    downloaderTested: boolean;
    rssTested: boolean;
    notificationTested: boolean;
  };
}

test.use({
  storageState: { cookies: [], origins: [] },
  viewport: MOBILE_VIEWPORT,
});

function setupDraft(currentStepIndex: number): SetupDraft {
  return {
    currentStepIndex,
    accountData: {
      username: 'mobile-admin',
      password: 'mobile-pass-9',
      confirmPassword: 'mobile-pass-9',
    },
    downloaderData: {
      type: 'qbittorrent',
      host: 'qb.internal:8080',
      username: '',
      password: '',
      path: '/downloads/Bangumi',
      ssl: false,
    },
    rssData: { url: '', name: '', skipped: false },
    notificationData: {
      enable: false,
      type: 'telegram',
      token: '',
      chat_id: '',
      skipped: false,
    },
    validation: {
      downloaderTested: false,
      rssTested: false,
      notificationTested: false,
    },
  };
}

async function prepareAnonymousPage(
  page: Page,
  options: {
    draft?: SetupDraft;
    needSetup?: boolean;
    supportPasskeys?: boolean;
  } = {}
): Promise<void> {
  await page.addInitScript(
    ({ draft, draftKey, supportPasskeys }) => {
      localStorage.setItem('isLoggedIn', 'false');
      localStorage.setItem('lang', 'en');
      localStorage.setItem('hasPasskey', 'false');
      sessionStorage.removeItem(draftKey);
      if (draft) sessionStorage.setItem(draftKey, JSON.stringify(draft));

      if (supportPasskeys) {
        Object.defineProperty(window, 'PublicKeyCredential', {
          configurable: true,
          value: class {},
        });
        Object.defineProperty(navigator, 'credentials', {
          configurable: true,
          value: {
            create: async () => null,
            get: async () => {
              throw new DOMException('E2E cancellation', 'NotAllowedError');
            },
          },
        });
      }
    },
    {
      draft: options.draft,
      draftKey: SETUP_DRAFT_KEY,
      supportPasskeys: options.supportPasskeys ?? false,
    }
  );

  await page.route('**/api/v1/setup/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        need_setup: options.needSetup ?? false,
        version: 'e2e',
      }),
    });
  });
}

async function openFirstRunSetup(
  page: Page,
  draft?: SetupDraft
): Promise<void> {
  await prepareAnonymousPage(page, { draft, needSetup: true });
  await page.goto('/#/');
  await expect(page).toHaveURL(/#\/setup$/);
}

async function expectTouchTarget(locator: Locator): Promise<void> {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeGreaterThanOrEqual(44);
  expect(box!.height).toBeGreaterThanOrEqual(44);
}

async function expectWithinViewport(locator: Locator, page: Page) {
  const box = await locator.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width);
  expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height);
}

async function expectHorizontallyWithinViewport(locator: Locator, page: Page) {
  const box = await locator.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport!.width);
}

test('mobile login stays bounded and scrollable after a short-height resize @mobile', async ({
  page,
}) => {
  await prepareAnonymousPage(page, { supportPasskeys: true });
  await page.goto('/#/login');

  expect(page.viewportSize()).toEqual(MOBILE_VIEWPORT);
  const card = page.locator('.login-card');
  const username = page.getByLabel('Username');
  const password = page.getByLabel('Password');
  const login = page.getByRole('button', { name: 'Login', exact: true });
  const passkey = page.getByRole('button', { name: 'Passkey', exact: true });
  await expectWithinViewport(card, page);
  for (const control of [username, password, login, passkey]) {
    await expectTouchTarget(control);
    await expectHorizontallyWithinViewport(control, page);
  }

  await page.setViewportSize(SHORT_VIEWPORT);
  const scrollMetrics = await page
    .locator('.page-login')
    .evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
  expect(scrollMetrics.scrollHeight).toBeGreaterThan(
    scrollMetrics.clientHeight
  );
  await expectHorizontallyWithinViewport(card, page);
  await passkey.scrollIntoViewIfNeeded();
  await expectWithinViewport(passkey, page);
});

test('password Enter sends exactly one intercepted login request @mobile', async ({
  page,
}) => {
  await prepareAnonymousPage(page);
  const submissions: string[] = [];
  await page.route('**/api/v1/auth/login', async (route) => {
    submissions.push(route.request().postData() ?? '');
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({
        msg_en: 'Expected E2E rejection',
        msg_zh: 'Expected E2E rejection',
      }),
    });
  });
  await page.goto('/#/login');

  await page.getByLabel('Username').fill('mobile-admin');
  const password = page.getByLabel('Password');
  await password.fill('mobile-pass-9');
  const response = page.waitForResponse(
    (candidate) =>
      candidate.url().endsWith('/api/v1/auth/login') &&
      candidate.request().method() === 'POST'
  );
  await password.press('Enter');
  await response;

  expect(submissions).toHaveLength(1);
  expect(submissions[0]).toContain('username=mobile-admin');
});

test('passkey action never submits the password form @mobile', async ({
  page,
}) => {
  await prepareAnonymousPage(page, { supportPasskeys: true });
  let passwordSubmissions = 0;
  let passkeyStarts = 0;
  await page.route('**/api/v1/auth/login', async (route) => {
    passwordSubmissions++;
    await route.fulfill({ status: 500, body: '' });
  });
  await page.route('**/api/v1/passkey/auth/options', async (route) => {
    passkeyStarts++;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        challenge: 'AQID',
        timeout: 1000,
        userVerification: 'preferred',
      }),
    });
  });
  await page.goto('/#/login');

  await page.getByLabel('Username').fill('mobile-admin');
  await page.getByLabel('Password').fill('mobile-pass-9');
  const passkeyResponse = page.waitForResponse((candidate) =>
    candidate.url().endsWith('/api/v1/passkey/auth/options')
  );
  await page.getByRole('button', { name: 'Passkey', exact: true }).click();
  await passkeyResponse;

  expect(passkeyStarts).toBe(1);
  expect(passwordSubmissions).toBe(0);
  await expect(page).toHaveURL(/#\/login$/);
});

test('mobile setup keeps progress and controls reachable after resize @mobile', async ({
  page,
}) => {
  await openFirstRunSetup(page);

  expect(page.viewportSize()).toEqual(MOBILE_VIEWPORT);
  const progress = page.getByRole('progressbar');
  await expect(progress).toHaveAttribute('aria-valuenow', '1');
  const progressBox = await progress.boundingBox();
  expect(progressBox).not.toBeNull();
  expect(progressBox!.y).toBeLessThan(80);
  const start = page.getByRole('button', { name: 'Get Started' });
  await expectTouchTarget(start);
  await start.click();

  const username = page.getByLabel('Username');
  const next = page.getByRole('button', { name: 'Next', exact: true });
  await expectTouchTarget(username);
  await expectTouchTarget(next);
  await page.setViewportSize(SHORT_VIEWPORT);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollHeight > window.innerHeight
    )
  ).toBe(true);
  await expectHorizontallyWithinViewport(
    page.locator('.wizard-container'),
    page
  );
  await next.scrollIntoViewIfNeeded();
  await expectWithinViewport(next, page);
  await progress.scrollIntoViewIfNeeded();
  await expectWithinViewport(progress, page);
});

test('setup account requires four username characters and matching eight-character passwords @mobile', async ({
  page,
}) => {
  await openFirstRunSetup(page, setupDraft(1));

  const username = page.getByLabel('Username');
  const password = page.getByLabel('Password', { exact: true });
  const confirmPassword = page.getByLabel('Confirm Password');
  const next = page.getByRole('button', { name: 'Next', exact: true });

  await username.fill('abc');
  await password.fill('12345678');
  await confirmPassword.fill('12345678');
  await expect(next).toBeDisabled();
  await username.fill('abcd');
  await password.fill('1234567');
  await confirmPassword.fill('1234567');
  await expect(next).toBeDisabled();
  await password.fill('12345678');
  await confirmPassword.fill('87654321');
  await expect(next).toBeDisabled();
  await confirmPassword.fill('12345678');
  await expect(next).toBeEnabled();
});

test('setup downloader can continue with only a host @mobile', async ({
  page,
}) => {
  const draft = setupDraft(2);
  draft.downloaderData.host = '';
  await openFirstRunSetup(page, draft);

  const next = page.getByRole('button', { name: 'Next', exact: true });
  const testConnection = page.getByRole('button', {
    name: 'Test Connection',
  });
  await expect(next).toBeDisabled();
  await page.getByLabel('Host').fill('qb.internal:8080');
  await expect(testConnection).toBeDisabled();
  await expect(next).toBeEnabled();
  await next.click();

  await expect(page.getByRole('progressbar')).toHaveAttribute(
    'aria-valuenow',
    '4'
  );
  await expect(page.getByText('RSS Source', { exact: true })).toBeVisible();
});

test('setup skips optional steps and completes through the explicit login route @mobile', async ({
  page,
}) => {
  await openFirstRunSetup(page, setupDraft(3));
  let completeCalls = 0;
  let completePayload: unknown;
  await page.route('**/api/v1/setup/complete', async (route) => {
    completeCalls++;
    completePayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: true }),
    });
  });
  await page.getByRole('button', { name: 'Skip', exact: true }).click();
  await expect(page.getByText('Notifications', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Skip', exact: true }).click();
  await expect(
    page.getByText('Review Settings', { exact: true })
  ).toBeVisible();
  const completeResponse = page.waitForResponse(
    (candidate) =>
      candidate.url().endsWith('/api/v1/setup/complete') &&
      candidate.request().method() === 'POST'
  );
  await page
    .getByRole('button', { name: 'Complete Setup', exact: true })
    .click();
  await completeResponse;

  expect(completeCalls).toBe(1);
  expect(completePayload).toMatchObject({
    username: 'mobile-admin',
    downloader_host: 'qb.internal:8080',
    downloader_username: '',
    rss_url: '',
    rss_name: '',
    notification_enable: false,
  });
  await expect(page).toHaveURL(/#\/login$/);
  await expect(
    page.getByRole('button', { name: 'Login', exact: true })
  ).toBeVisible();
});
