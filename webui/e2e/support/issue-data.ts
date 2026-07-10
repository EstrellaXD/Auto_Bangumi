import type { APIRequestContext, APIResponse } from '@playwright/test';
import type { E2EEnvironment } from '../fixtures/env';

interface ApiConfig {
  network: Record<string, unknown>;
  rss_parser: Record<string, unknown>;
  update: Record<string, unknown>;
  [group: string]: unknown;
}

export interface BangumiRecord {
  id: number;
  official_title: string;
  title_raw: string;
  season: number;
  episode_offset: number;
  air_weekday: number | null;
  weekday_locked: boolean;
  needs_review: boolean;
  needs_review_reason: string | null;
  preferred_group: string | null;
  [key: string]: unknown;
}

interface SeedRuleOptions {
  title: string;
  uniqueName: string;
  rawTitle?: string;
}

async function requireStatus(
  response: APIResponse,
  expected: number | number[]
): Promise<APIResponse> {
  const statuses = Array.isArray(expected) ? expected : [expected];
  if (!statuses.includes(response.status())) {
    throw new Error(
      `${response.url()} returned ${response.status()}, expected ${statuses.join(
        ' or '
      )}`
    );
  }
  return response;
}

export async function resetRules(request: APIRequestContext): Promise<void> {
  await requireStatus(await request.post('/api/v1/bangumi/reset/all'), 200);
}

export async function configureLocalMetadata(
  request: APIRequestContext,
  environment: E2EEnvironment,
  language: 'zh' | 'en' | 'jp'
): Promise<void> {
  const current = await requireStatus(
    await request.get('/api/v1/config/get'),
    200
  );
  const config = (await current.json()) as ApiConfig;
  config.network.tmdb_base_url = `${environment.mockInternalURL}/tmdb`;
  config.network.bgm_base_url = `${environment.mockInternalURL}/bgm`;
  config.rss_parser.language = language;
  config.update.auto_check = false;
  await requireStatus(
    await request.patch('/api/v1/config/update', { data: config }),
    200
  );
}

async function mockAdmin(
  environment: E2EEnvironment,
  path: string,
  method: 'GET' | 'POST' | 'PUT' = 'GET'
): Promise<Response> {
  const response = await fetch(`${environment.mockURL}${path}`, { method });
  if (!response.ok)
    throw new Error(`Mock admin ${method} ${path} returned ${response.status}`);
  return response;
}

export async function resetMock(environment: E2EEnvironment): Promise<void> {
  await mockAdmin(environment, '/__admin/reset', 'POST');
}

export async function activateTmdbScenario(
  environment: E2EEnvironment,
  scenario: string
): Promise<void> {
  await mockAdmin(environment, `/__admin/scenario/${scenario}`, 'PUT');
}

export async function mockRequests(
  environment: E2EEnvironment
): Promise<Array<Record<string, unknown>>> {
  const response = await mockAdmin(environment, '/__admin/requests');
  const payload = (await response.json()) as {
    requests: Array<Record<string, unknown>>;
  };
  return payload.requests;
}

export async function analyseTmdbFixture(
  request: APIRequestContext,
  environment: E2EEnvironment,
  fixture = 'tmdb-tv.xml'
): Promise<BangumiRecord> {
  const response = await requireStatus(
    await request.post('/api/v1/rss/analysis', {
      data: {
        name: fixture,
        url: `${environment.mockInternalURL}/rss/${fixture}`,
        aggregate: false,
        parser: 'tmdb',
        enabled: true,
      },
    }),
    200
  );
  return response.json();
}

async function analyseParserFixture(
  request: APIRequestContext,
  environment: E2EEnvironment
): Promise<BangumiRecord> {
  const response = await requireStatus(
    await request.post('/api/v1/rss/analysis', {
      data: {
        name: 'tmdb-tv.xml',
        url: `${environment.mockInternalURL}/rss/tmdb-tv.xml`,
        aggregate: false,
        parser: 'parser',
        enabled: true,
      },
    }),
    200
  );
  return response.json();
}

export async function listRules(
  request: APIRequestContext
): Promise<BangumiRecord[]> {
  const response = await requireStatus(
    await request.get('/api/v1/bangumi/get/all'),
    200
  );
  return response.json();
}

export async function seedRule(
  request: APIRequestContext,
  environment: E2EEnvironment,
  options: SeedRuleOptions
): Promise<BangumiRecord> {
  const rssURL = `${environment.mockInternalURL}/rss/tmdb-tv.xml`;
  const analysed = await analyseParserFixture(request, environment);
  const data: Record<string, unknown> = { ...analysed };
  delete data.id;
  delete data.suggested_season_offset;
  delete data.suggested_episode_offset;
  Object.assign(data, {
    official_title: options.title,
    title_raw: options.rawTitle ?? `${options.title} ${options.uniqueName}`,
    rss_link: rssURL,
    rule_name: options.uniqueName,
    added: true,
    needs_review: false,
    needs_review_reason: null,
  });

  // The browser profile's qB fake intentionally rejects torrent adds. The
  // production subscribe path inserts the rule first and reports that add as
  // 502, which is sufficient for UI rule fixtures without an offline DB hook.
  await requireStatus(
    await request.post('/api/v1/rss/subscribe', {
      data: {
        data,
        rss: {
          name: `seed-${options.uniqueName}`,
          url: rssURL,
          aggregate: false,
          parser: 'parser',
          enabled: true,
        },
      },
    }),
    502
  );

  const created = (await listRules(request)).find(
    (rule) => rule.title_raw === data.title_raw
  );
  if (!created) throw new Error(`Rule ${options.uniqueName} was not persisted`);
  return created;
}

export async function patchFullRule(
  request: APIRequestContext,
  rule: BangumiRecord,
  changes: Record<string, unknown>
): Promise<BangumiRecord> {
  const payload: Record<string, unknown> = { ...rule, ...changes };
  delete payload.id;
  delete payload.suggested_season_offset;
  delete payload.suggested_episode_offset;
  await requireStatus(
    await request.patch(`/api/v1/bangumi/update/${rule.id}`, {
      data: payload,
    }),
    200
  );
  const updated = (await listRules(request)).find(
    (candidate) => candidate.id === rule.id
  );
  if (!updated) throw new Error(`Rule ${rule.id} disappeared after update`);
  return updated;
}
