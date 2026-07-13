import { E2EApi } from '../fixtures/api';
import {
  closeAuthenticatedContexts,
  forceEnglish,
  loginThroughUI,
  newAuthenticatedContext,
} from '../fixtures/auth';
import { SESSION_SUCCESS } from '../fixtures/data';
import { expect, test } from '../fixtures/test';

test('refresh keeps a cookie-only session without exposing a token', async ({
  page,
}) => {
  const refreshResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/refresh_token') &&
      response.request().method() === 'POST'
  );
  await page.goto('/#/bangumi');

  const response = await refreshResponse;
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual(SESSION_SUCCESS);

  const tokenCookie = (await page.context().cookies()).find(
    (cookie) => cookie.name === 'token'
  );
  expect(tokenCookie).toMatchObject({ httpOnly: true, sameSite: 'Strict' });
});

test('wrong password is rejected without leaving the login page', async ({
  page,
  environment,
}) => {
  await page.context().clearCookies();
  await forceEnglish(page);
  await page.addInitScript(() => localStorage.setItem('isLoggedIn', 'false'));
  await loginThroughUI(
    page,
    { username: environment.username, password: 'definitely-wrong' },
    401
  );

  await expect(page).toHaveURL(/#\/login$/);
  expect(
    (await page.context().cookies()).some((cookie) => cookie.name === 'token')
  ).toBe(false);
});

test('logout and browser back cannot revive a revoked session', async ({
  browser,
  environment,
}, testInfo) => {
  const authenticated = await newAuthenticatedContext(
    browser,
    environment,
    environment,
    testInfo
  );
  const { page } = authenticated;
  try {
    await page.goto('/#/bangumi');
    const api = new E2EApi(page.context().request);
    await api.logout();

    await page.reload();
    await expect(page).toHaveURL(/#\/login$/);
    await page.goBack();
    await expect(page).not.toHaveURL(/#\/bangumi$/);
    await page.goto('/#/bangumi');
    await expect(page).toHaveURL(/#\/login$/);
  } finally {
    await closeAuthenticatedContexts([authenticated], testInfo);
  }
});
