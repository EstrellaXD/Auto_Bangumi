import {
  closeAuthenticatedContexts,
  newAuthenticatedContext,
} from '../fixtures/auth';
import { expect, test } from '../fixtures/test';

test('player settings stay browser-local and load the hermetic iframe', async ({
  browser,
  environment,
  page,
}, testInfo) => {
  const backendMutations: string[] = [];
  page.on('request', (request) => {
    if (
      (request.url().endsWith('/api/v1/config/update') &&
        request.method() === 'PATCH') ||
      (request.url().endsWith('/api/v1/restart') && request.method() === 'POST')
    )
      backendMutations.push(request.url());
  });

  const configLoaded = page.waitForResponse((response) =>
    response.url().endsWith('/api/v1/config/get')
  );
  await page.goto('/#/config');
  await configLoaded;

  const playerPanel = page
    .getByRole('button', { name: 'Media Player Setting', exact: true })
    .locator('..');
  await playerPanel.getByLabel('Type').click();
  await page.getByRole('option', { name: 'iframe', exact: true }).click();
  const playerURL = `${environment.mockURL}/player/`;
  await playerPanel.getByLabel('Player URL').fill(playerURL);

  await expect(
    page.getByRole('button', { name: 'Save & restart' })
  ).toBeDisabled();
  await expect
    .poll(() =>
      page.evaluate(() => ({
        type: localStorage.getItem('media-player-type'),
        url: localStorage.getItem('media-player-url'),
      }))
    )
    .toEqual({ type: 'iframe', url: playerURL });
  expect(backendMutations).toEqual([]);

  await page.reload();
  const reloadedPanel = page
    .getByRole('button', { name: 'Media Player Setting', exact: true })
    .locator('..');
  await expect(reloadedPanel.getByLabel('Player URL')).toHaveValue(playerURL);

  await page.goto('/#/player');
  const frame = page.locator('iframe[title="Player"]');
  await expect(frame).toBeVisible();
  await expect(frame).toHaveAttribute('src', playerURL);
  await expect(
    page.frameLocator('iframe[title="Player"]').locator('#e2e-player-marker')
  ).toHaveText('Hermetic player fixture loaded');
  expect(backendMutations).toEqual([]);

  const isolated = await newAuthenticatedContext(
    browser,
    environment,
    environment,
    testInfo
  );
  try {
    await isolated.page.goto('/#/config');
    const isolatedPanel = isolated.page
      .getByRole('button', { name: 'Media Player Setting', exact: true })
      .locator('..');
    await expect(isolatedPanel.getByLabel('Type')).toContainText('jump');
    await expect(isolatedPanel.getByLabel('Player URL')).toHaveValue('');
  } finally {
    await closeAuthenticatedContexts([isolated], testInfo);
  }
});
