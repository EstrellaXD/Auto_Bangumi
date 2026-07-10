import { expect, test } from '../fixtures/test';
import {
  listRules,
  patchFullRule,
  resetRules,
  seedRule,
} from '../support/issue-data';

const ISSUE_1072_TITLE =
  '[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 06v2 ' +
  '(1080p) [E931DD98].mkv';
const OVERFLOW_TITLE =
  '[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 13 ' +
  '(1080p) [ABCDEF12].mkv';

test('real issue titles distinguish a versioned episode from an offset overflow', async ({
  environment,
  page,
  request,
  uniqueName,
}) => {
  await resetRules(request);

  try {
    const negativeSeed = await seedRule(request, environment, {
      title: 'Issue 1072 Negative',
      uniqueName: `${uniqueName}-negative`,
      rawTitle: ISSUE_1072_TITLE,
    });
    const negative = await patchFullRule(request, negativeSeed, {
      needs_review: false,
      needs_review_reason: null,
    });
    expect(negative).toMatchObject({
      title_raw: ISSUE_1072_TITLE,
      needs_review: false,
      needs_review_reason: null,
    });

    await page.goto('/#/bangumi');
    await page
      .getByRole('button', { name: 'Edit Issue 1072 Negative', exact: true })
      .click();
    const negativeDialog = page.getByRole('dialog', { name: 'Edit Rule' });
    await expect(
      negativeDialog.getByRole('status', { name: 'Offset Review Needed' })
    ).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(negativeDialog).toHaveCount(0);

    await resetRules(request);
    const reason = 'Episode 13 exceeds TMDB count of 12';
    const positiveSeed = await seedRule(request, environment, {
      title: 'Issue 1072 Positive',
      uniqueName: `${uniqueName}-positive`,
      rawTitle: OVERFLOW_TITLE,
    });
    const rule = await patchFullRule(request, positiveSeed, {
      needs_review: true,
      needs_review_reason: reason,
    });
    expect(rule).toMatchObject({
      title_raw: OVERFLOW_TITLE,
      needs_review: true,
      needs_review_reason: reason,
    });

    const rulesLoaded = page.waitForResponse((response) =>
      response.url().endsWith('/api/v1/bangumi/get/all')
    );
    await page.reload();
    await rulesLoaded;
    await page
      .getByRole('button', { name: 'Edit Issue 1072 Positive', exact: true })
      .click();

    const dialog = page.getByRole('dialog', { name: 'Edit Rule' });
    const review = dialog.getByRole('status', {
      name: 'Offset Review Needed',
    });
    await expect(review).toContainText(reason);

    const dismissed = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/v1/bangumi/dismiss-review/${rule.id}`) &&
        response.request().method() === 'POST'
    );
    await review.getByRole('button', { name: 'Dismiss' }).click();
    expect((await dismissed).status()).toBe(200);
    await expect(review).toHaveCount(0);

    const persisted = (await listRules(request)).find(
      (item) => item.id === rule.id
    );
    expect(persisted?.needs_review).toBe(false);
    expect(persisted?.needs_review_reason).toBeNull();
  } finally {
    await resetRules(request);
  }
});
