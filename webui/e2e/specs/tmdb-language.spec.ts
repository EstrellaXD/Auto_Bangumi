import { expect, test } from '../fixtures/test';
import {
  activateTmdbScenario,
  analyseTmdbFixture,
  configureLocalMetadata,
  mockRequests,
  resetMock,
} from '../support/issue-data';

test('changing parser language re-queries the same TMDB title in that locale', async ({
  environment,
  page,
  request,
}) => {
  await resetMock(environment);
  await configureLocalMetadata(request, environment, 'zh');
  await activateTmdbScenario(environment, 'localized-tv-zh');

  const chinese = await analyseTmdbFixture(request, environment);
  expect(chinese.official_title).toBe('本地化动画');

  const configLoaded = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/config/get') &&
      response.request().method() === 'GET'
  );
  await page.goto('/#/config');
  await configLoaded;

  const parserPanel = page
    .getByRole('button', { name: 'Parser Setting', exact: true })
    .locator('..');
  await parserPanel.getByLabel('Language').click();
  await page.getByRole('option', { name: 'jp', exact: true }).click();

  await page.getByRole('button', { name: 'Save & restart' }).click();
  const confirmation = page.getByRole('dialog', {
    name: 'Save & restart',
  });
  const updateResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/config/update') &&
      response.request().method() === 'PATCH'
  );
  const restartResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/restart') &&
      response.request().method() === 'POST'
  );
  await confirmation
    .getByRole('button', { name: 'Save & restart', exact: true })
    .click();
  const [updated, restarted] = await Promise.all([
    updateResponse,
    restartResponse,
  ]);
  expect(updated.status()).toBe(200);
  expect(restarted.status()).toBe(200);

  await activateTmdbScenario(environment, 'localized-tv-jp');
  const japanese = await analyseTmdbFixture(request, environment);
  expect(japanese.official_title).toBe('ローカライズアニメ');

  await activateTmdbScenario(environment, 'localized-movie-jp');
  const movie = await analyseTmdbFixture(
    request,
    environment,
    'tmdb-movie.xml'
  );
  expect(movie).toMatchObject({
    official_title: 'ローカライズ映画',
    episode_type: 'movie',
  });

  await activateTmdbScenario(environment, 'localized-retry-jp');
  const retried = await analyseTmdbFixture(
    request,
    environment,
    'tmdb-retry.xml'
  );
  expect(retried.official_title).toBe('再試行アニメ');

  const searches = (await mockRequests(environment)).filter((entry) =>
    String(entry.path).startsWith('/tmdb/3/search/')
  );
  const queryValue = (entry: Record<string, unknown>, key: string) => {
    const query = entry.query as Record<string, string[]>;
    return query[key]?.[0];
  };
  const languages = searches.map((entry) => queryValue(entry, 'language'));
  expect(languages).toContain('zh-CN');
  expect(languages).toContain('ja-JP');
  expect(
    searches.some(
      (entry) =>
        entry.path === '/tmdb/3/search/movie' &&
        queryValue(entry, 'query') === 'Localized Movie' &&
        queryValue(entry, 'language') === 'ja-JP'
    )
  ).toBe(true);
  const retryQueries = searches
    .filter(
      (entry) =>
        entry.path === '/tmdb/3/search/tv' &&
        queryValue(entry, 'language') === 'ja-JP'
    )
    .map((entry) => queryValue(entry, 'query'));
  expect(retryQueries.slice(-2)).toEqual([
    'Retry Localized Show',
    'RetryLocalizedShow',
  ]);
});
