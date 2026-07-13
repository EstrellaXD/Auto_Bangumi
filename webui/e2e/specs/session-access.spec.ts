import { request as playwrightRequest } from '@playwright/test';
import { E2EApi } from '../fixtures/api';
import type { AuthenticatedContext } from '../fixtures/auth';
import {
  closeAuthenticatedContexts,
  loginThroughUI,
  newAuthenticatedContext,
} from '../fixtures/auth';
import type { ApiTokenCreated } from '../fixtures/data';
import { SESSION_SUCCESS, changedPassword } from '../fixtures/data';
import { expect, test } from '../fixtures/test';

test('password change rotates both browser contexts and rejects the old password', async ({
  api,
  browser,
  environment,
  uniqueName,
}, testInfo) => {
  const credentials = {
    username: `u-${uniqueName.slice(-16)}`,
    password: 'Initial-Password9!',
  };
  const user = await api.createUser(credentials);
  let first: AuthenticatedContext | undefined;
  let second: AuthenticatedContext | undefined;
  let cleanupFailure: unknown;

  try {
    first = await newAuthenticatedContext(
      browser,
      environment,
      credentials,
      testInfo
    );
    second = await newAuthenticatedContext(
      browser,
      environment,
      credentials,
      testInfo
    );

    await first.page.getByRole('button', { name: 'System menu' }).click();
    await first.page.getByRole('menuitem', { name: 'Profile' }).click();
    const dialog = first.page.getByRole('dialog').last();
    const nextCredentials = {
      username: credentials.username,
      password: changedPassword(uniqueName),
    };
    await dialog.getByLabel('Username').fill(nextCredentials.username);
    await dialog
      .getByLabel('Password', { exact: true })
      .fill(nextCredentials.password);
    const updateResponse = first.page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/v1/auth/update') &&
        response.request().method() === 'POST'
    );
    await dialog.getByRole('button', { name: 'Update' }).click();
    expect(await (await updateResponse).json()).toEqual(SESSION_SUCCESS);

    await new E2EApi(second.context.request).me(401);
    await second.context.clearCookies();
    await second.page.evaluate(() =>
      localStorage.setItem('isLoggedIn', 'false')
    );
    await second.page.reload();
    await expect(second.page).toHaveURL(/#\/login$/);
    await loginThroughUI(second.page, credentials, 401);
    await loginThroughUI(second.page, nextCredentials);
    await expect(second.page).toHaveURL(/#\/bangumi$/);
  } finally {
    const contexts = [first, second].filter(
      (value): value is AuthenticatedContext => value !== undefined
    );
    const cleanup = await Promise.allSettled([
      closeAuthenticatedContexts(contexts, testInfo),
      api.deleteUser(user.id),
    ]);
    const failure = cleanup.find(
      (result): result is PromiseRejectedResult => result.status === 'rejected'
    );
    cleanupFailure = failure?.reason;
  }
  if (cleanupFailure) throw cleanupFailure;
});

test('API and MCP tokens are isolated and Bearer cannot control accounts', async ({
  api,
  environment,
  uniqueName,
}) => {
  const bearerContext = await playwrightRequest.newContext({
    baseURL: environment.baseURL,
  });
  const bearerApi = new E2EApi(bearerContext);
  const tokens: ApiTokenCreated[] = [];
  let cleanupFailure: unknown;

  try {
    const apiToken = await api.createToken(`${uniqueName}-api`, 'api');
    tokens.push(apiToken);
    const mcpToken = await api.createToken(`${uniqueName}-mcp`, 'mcp');
    tokens.push(mcpToken);

    await bearerApi.bearerGet('/api/v1/bangumi/get/all', apiToken.token, 200);
    await bearerApi.bearerGet('/api/v1/users', apiToken.token, 403);
    await bearerApi.bearerGet('/api/v1/tokens', apiToken.token, 403);
    await bearerApi.bearerGet('/api/v1/bangumi/get/all', mcpToken.token, 401);
    await bearerApi.bearerGet('/mcp/sse', apiToken.token, 403);

    // An explicit invalid Authorization header must beat the valid admin cookie.
    await api.bearerGet('/api/v1/bangumi/get/all', mcpToken.token, 401);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(`${environment.baseURL}/mcp/sse`, {
        headers: { Authorization: `Bearer ${mcpToken.token}` },
        signal: controller.signal,
      });
      expect(response.status).toBe(200);
    } finally {
      clearTimeout(timeout);
      controller.abort();
    }
  } finally {
    const cleanup = await Promise.allSettled([
      bearerContext.dispose(),
      ...tokens.map((token) => api.revokeToken(token.id)),
    ]);
    const failure = cleanup.find(
      (result): result is PromiseRejectedResult => result.status === 'rejected'
    );
    cleanupFailure = failure?.reason;
  }
  if (cleanupFailure) throw cleanupFailure;
});
