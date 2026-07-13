import type { Locator } from '@playwright/test';

import { expect, test } from '../fixtures/test';
import { listRules, resetRules, seedRule } from '../support/issue-data';

async function ensureAdvancedSettingsOpen(dialog: Locator) {
  const toggle = dialog.getByRole('button', { name: 'Advanced Settings' });

  if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
    await toggle.click();
  }

  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
}

test('mobile rule editor saves advanced keyboard-accessible fields @mobile', async ({
  environment,
  page,
  request,
  uniqueName,
}) => {
  await resetRules(request);
  const rule = await seedRule(request, environment, {
    title: 'Mobile Rule Fixture',
    uniqueName,
  });

  try {
    expect(page.viewportSize()).toEqual({ width: 390, height: 844 });
    await page.goto('/#/bangumi');
    await page
      .getByRole('button', {
        name: 'Edit Mobile Rule Fixture',
        exact: true,
      })
      .click();

    const dialog = page.getByRole('dialog', { name: 'Edit Rule' });
    const panel = dialog.getByTestId('bottom-sheet-panel');
    const initialBox = await panel.boundingBox();
    expect(initialBox).not.toBeNull();
    expect(initialBox!.x).toBeCloseTo(0, 0);
    expect(initialBox!.y).toBeCloseTo(0, 0);
    expect(initialBox!.width).toBeCloseTo(390, 0);
    expect(initialBox!.height).toBeCloseTo(844, 0);

    const title = dialog.getByLabel('Official Title');
    await title.fill('Mobile Rule Updated');
    await title.focus();
    await page.setViewportSize({ width: 390, height: 600 });
    await expect(panel).toHaveCSS('transform', 'none');
    const shrunkenBox = await panel.boundingBox();
    expect(shrunkenBox).not.toBeNull();
    expect(shrunkenBox!.y).toBeCloseTo(0, 0);
    expect(shrunkenBox!.height).toBeCloseTo(600, 0);
    await page.setViewportSize({ width: 390, height: 844 });

    await ensureAdvancedSettingsOpen(dialog);
    await dialog.getByLabel('Episode Offset').fill('3');
    await dialog.getByLabel('Preferred group').fill('E2E Preferred');
    await dialog.getByLabel('Air Weekday').click();
    await page.getByRole('option', { name: 'Friday', exact: true }).click();

    const updateResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/v1/bangumi/update/${rule.id}`) &&
        response.request().method() === 'PATCH'
    );
    await dialog.getByRole('button', { name: 'Apply', exact: true }).click();
    const response = await updateResponse;
    expect(response.status()).toBe(200);
    expect(response.request().postDataJSON()).toMatchObject({
      official_title: 'Mobile Rule Updated',
      episode_offset: 3,
      preferred_group: 'E2E Preferred',
      air_weekday: 4,
      weekday_locked: true,
    });
    await expect(dialog).toHaveCount(0);

    const persisted = (await listRules(request)).find(
      (item) => item.id === rule.id
    );
    expect(persisted).toMatchObject({
      official_title: 'Mobile Rule Updated',
      episode_offset: 3,
      preferred_group: 'E2E Preferred',
      air_weekday: 4,
      weekday_locked: true,
    });

    await page.reload();
    await page
      .getByRole('button', { name: 'Edit Mobile Rule Updated', exact: true })
      .click();
    const reloaded = page.getByRole('dialog', { name: 'Edit Rule' });
    await expect(reloaded.getByLabel('Official Title')).toHaveValue(
      'Mobile Rule Updated'
    );
    await ensureAdvancedSettingsOpen(reloaded);
    await expect(reloaded.getByLabel('Episode Offset')).toHaveValue('3');
    await expect(reloaded.getByLabel('Preferred group')).toHaveValue(
      'E2E Preferred'
    );
    await expect(reloaded.getByLabel('Air Weekday')).toContainText('Friday');
  } finally {
    await resetRules(request);
  }
});
