import { createHash } from 'node:crypto';
import type { Page, Route } from '@playwright/test';
import type { ApiTokenCreated } from '../fixtures/data';
import { expect, test } from '../fixtures/test';

// A screenshot or video of the reveal dialog is itself a secret leak.  This
// spec relies on the redacted NetworkGuard diagnostics instead.
test.use({ screenshot: 'off', trace: 'off', video: 'off' });

function sha256(value: string): string {
  return createHash('sha256').update(value).digest('hex');
}

async function expectSecretMatches(page: Page, secret: string): Promise<void> {
  const revealed = await page.getByLabel('One-time token').textContent();
  expect(sha256(revealed ?? '')).toBe(sha256(secret));
}

async function expectSecretAbsent(page: Page, secret: string): Promise<void> {
  const body = await page.locator('body').innerText();
  expect(body.includes(secret)).toBe(false);
}

async function openAccess(page: Page): Promise<void> {
  await page.goto('/#/config');
  await expect(page).toHaveURL(/#\/config$/);
  const accessPanel = page
    .getByRole('button', { name: 'Users & Access', exact: true })
    .last();
  await expect(accessPanel).toBeVisible();
}

async function openBangumi(page: Page): Promise<void> {
  await page.goto('/#/bangumi');
  await expect(page).toHaveURL(/#\/bangumi$/);
  await expect(
    page.getByRole('button', { name: 'Add RSS Feed', exact: true })
  ).toBeVisible();
}

async function createTokenFromUI(
  page: Page,
  name: string
): Promise<ApiTokenCreated> {
  await page.getByRole('button', { name: 'Create token' }).click();
  await page.getByLabel('Token name').fill(name);
  const createResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/tokens') &&
      response.request().method() === 'POST'
  );
  await page.getByRole('button', { name: 'Create', exact: true }).click();
  const response = await createResponse;
  expect(response.status()).toBe(201);
  const created = (await response.json()) as ApiTokenCreated;
  return created;
}

test('one-time token disappears on close and never appears in the list', async ({
  page,
  api,
  uniqueName,
}) => {
  await openAccess(page);
  let created: ApiTokenCreated | null = null;
  try {
    created = await createTokenFromUI(page, `${uniqueName}-close`);
    await expectSecretMatches(page, created.token);
    const revealDialog = page.getByRole('dialog', { name: 'Token created' });
    await revealDialog.getByRole('button', { name: 'Close' }).click();
    await expect(page.getByLabel('One-time token')).toHaveCount(0);

    await openBangumi(page);
    await openAccess(page);
    const tokenRow = page.getByRole('group', { name: created.name });
    await expect(tokenRow).toContainText(created.prefix);
    await expectSecretAbsent(page, created.token);
    expect((await tokenRow.innerText()).includes(created.token)).toBe(false);
  } finally {
    if (created) await api.revokeToken(created.id);
  }
});

function requireCreatedToken(created: ApiTokenCreated | null): ApiTokenCreated {
  if (!created) throw new Error('The delayed token request was never created');
  return created;
}

test('late token response cannot restore a secret after navigation', async ({
  page,
  api,
  uniqueName,
}) => {
  let releaseResponse!: () => void;
  const release = new Promise<void>((resolve) => {
    releaseResponse = resolve;
  });
  let upstreamReady!: () => void;
  const ready = new Promise<void>((resolve) => {
    upstreamReady = resolve;
  });
  let routeSettled!: () => void;
  const settled = new Promise<void>((resolve) => {
    routeSettled = resolve;
  });
  let created: ApiTokenCreated | null = null;
  let handlerStarted = false;
  let responseDelivered = false;
  let deliveryFailure: unknown;
  let cleanupFailure: unknown;
  const tokenName = `${uniqueName}-late`;

  const handleTokenRoute = async (route: Route) => {
    if (route.request().method() !== 'POST') {
      await route.continue();
      return;
    }
    handlerStarted = true;
    try {
      const response = await route.fetch();
      expect(response.status()).toBe(201);
      created = (await response.json()) as ApiTokenCreated;
      upstreamReady();
      await release;
      try {
        await route.fulfill({ response });
        responseDelivered = true;
      } catch (error) {
        deliveryFailure = error;
      }
    } finally {
      routeSettled();
    }
  };
  await page.route('**/api/v1/tokens', handleTokenRoute);

  try {
    await openAccess(page);
    await page.getByRole('button', { name: 'Create token' }).click();
    await page.getByLabel('Token name').fill(tokenName);
    await page.getByRole('button', { name: 'Create', exact: true }).click();
    await ready;

    // An in-document hash change keeps the pending fetch alive in WebKit.  The
    // destination sentinel proves KeepAlive deactivated Config before the
    // intercepted response is delivered.  The modal makes the navigation
    // links inert while the create request is pending, so drive the same hash
    // router transition directly.
    await page.evaluate(() => {
      window.location.hash = '#/bangumi';
    });
    await expect(page).toHaveURL(/#\/bangumi$/);
    await expect(
      page.getByRole('button', { name: 'Add RSS Feed', exact: true })
    ).toBeVisible();
    releaseResponse();
    await settled;
    if (deliveryFailure) throw deliveryFailure;
    expect(responseDelivered).toBe(true);

    const issued = requireCreatedToken(created);
    await expectSecretAbsent(page, issued.token);
    await openAccess(page);

    const tokenRow = page.getByRole('group', { name: issued.name });
    await expect(tokenRow).toContainText(issued.prefix);
    await expect(page.getByLabel('One-time token')).toHaveCount(0);
    await expectSecretAbsent(page, issued.token);
  } finally {
    releaseResponse();
    const unroute = await Promise.allSettled([
      page.unroute('**/api/v1/tokens', handleTokenRoute),
    ]);
    if (handlerStarted) await settled;

    const revoke = await Promise.allSettled([
      api.listTokens().then(async (tokens) => {
        const matching = tokens.filter(
          (token) => token.name === tokenName && token.revoked_at === null
        );
        await Promise.all(matching.map((token) => api.revokeToken(token.id)));
      }),
    ]);
    const failure = [...unroute, ...revoke].find(
      (result): result is PromiseRejectedResult => result.status === 'rejected'
    );
    cleanupFailure = failure?.reason;
  }
  if (cleanupFailure) throw cleanupFailure;
});
