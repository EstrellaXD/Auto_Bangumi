import { expect, test } from '../fixtures/test';

test('production shell and health endpoint are served', async ({
  page,
  request,
}) => {
  const health = await request.get('/health');
  expect(health.ok()).toBe(true);
  await expect(health.json()).resolves.toMatchObject({
    status: 'ok',
    db_ok: true,
  });

  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', /.+/);
  const assets = await page
    .locator('script[src], link[rel="stylesheet"]')
    .evaluateAll((elements) =>
      elements.map(
        (element) => element.getAttribute('src') ?? element.getAttribute('href')
      )
    );
  expect(assets.some((asset) => asset?.includes('/assets/'))).toBe(true);
});
