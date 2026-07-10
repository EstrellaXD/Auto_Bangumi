import { createHash } from 'node:crypto';
import { readFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import {
  type APIRequestContext,
  type APIResponse,
  request as playwrightRequest,
} from '@playwright/test';
import { expect, test } from '../fixtures/test';

interface QbTorrent {
  hash: string;
  name: string;
  num_leechs: number;
  num_seeds: number;
  progress: number;
  save_path: string;
  state: string;
  tags: string;
  tracker: string;
}

interface QbFile {
  name: string;
  progress: number;
  size: number;
}

interface RuntimeConfig {
  program: { rename_time: number; rss_time: number };
  rss_parser: { enable: boolean };
  bangumi_manage: { enable: boolean; rename_method: string };
  network: { bgm_base_url: string; tmdb_base_url: string };
  update: { auto_check: boolean };
}

interface BangumiRecord {
  id: number;
  official_title: string;
  save_path: string;
}

interface RssRecord {
  id: number;
  url: string;
}

async function expectStatus(
  response: APIResponse,
  expected = 200
): Promise<APIResponse> {
  if (response.status() !== expected) {
    throw new Error(
      `${response.url()} returned ${response.status()}, expected ${expected}: ${(
        await response.text()
      ).slice(0, 1000)}`
    );
  }
  return response;
}

async function qbTorrents(qb: APIRequestContext): Promise<QbTorrent[]> {
  const response = await expectStatus(
    await qb.get('/api/v2/torrents/info', {
      params: { category: 'Bangumi' },
    })
  );
  return response.json();
}

async function fileState(path: string): Promise<{
  exists: boolean;
  sha256: string | null;
  size: number | null;
}> {
  try {
    const [metadata, content] = await Promise.all([stat(path), readFile(path)]);
    return {
      exists: true,
      sha256: createHash('sha256').update(content).digest('hex'),
      size: metadata.size,
    };
  } catch {
    return { exists: false, sha256: null, size: null };
  }
}

test('@downloader RSS reaches real qB, completes, renames, and deletes', async ({
  environment,
  page,
  request,
}) => {
  test.setTimeout(90_000);
  expect(environment.profile).toBe('downloader');
  expect(environment.realQbURL).not.toBeNull();

  const qb = await playwrightRequest.newContext({
    baseURL: environment.realQbURL!,
  });
  try {
    const login = await qb.post('/api/v2/auth/login', {
      form: {
        username: environment.downloaderUsername,
        password: environment.downloaderPassword,
      },
    });
    expect([200, 204]).toContain(login.status());
    if (login.status() === 200) expect((await login.text()).trim()).toBe('Ok.');

    const preferences = await (
      await expectStatus(await qb.get('/api/v2/app/preferences'))
    ).json();
    expect(preferences).toMatchObject({
      dht: false,
      lsd: false,
      pex: false,
      rss_auto_downloading_enabled: false,
      rss_processing_enabled: false,
      save_path: '/downloads/Bangumi',
      upnp: false,
    });
    expect(await qbTorrents(qb)).toEqual([]);
    await expectStatus(
      await request.post(`${environment.mockURL}/__admin/reset`)
    );

    const configResponse = await expectStatus(
      await request.get('/api/v1/config/get')
    );
    const config = (await configResponse.json()) as RuntimeConfig;
    config.program.rename_time = 1;
    config.program.rss_time = 3600;
    config.rss_parser.enable = false;
    config.bangumi_manage.enable = true;
    config.bangumi_manage.rename_method = 'pn';
    config.network.tmdb_base_url = `${environment.mockInternalURL}/tmdb`;
    config.network.bgm_base_url = `${environment.mockInternalURL}/bgm`;
    config.update.auto_check = false;
    await expectStatus(
      await request.patch('/api/v1/config/update', { data: config })
    );

    const rss = {
      aggregate: false,
      enabled: true,
      name: 'Tiny Download E2E',
      parser: 'parser',
      url: `${environment.mockInternalURL}/rss/tiny-download.xml`,
    };
    const analysis = await expectStatus(
      await request.post('/api/v1/rss/analysis', { data: rss })
    );
    const analysedBangumi = await analysis.json();
    expect(analysedBangumi).toMatchObject({
      episode_type: 'episode',
      official_title: 'Tiny Show',
      season: 1,
    });

    await expectStatus(
      await request.post('/api/v1/rss/subscribe', {
        data: { data: analysedBangumi, rss },
      })
    );

    let completedTorrent: QbTorrent | undefined;
    await expect
      .poll(
        async () => {
          const torrents = await qbTorrents(qb);
          completedTorrent = torrents[0];
          return torrents.map((torrent) => ({
            progress: torrent.progress,
            savePath: torrent.save_path.replace(/\/$/, ''),
          }));
        },
        {
          intervals: [100, 250, 500, 1000],
          message: 'real qBittorrent should finish the local web-seed torrent',
          timeout: 45_000,
        }
      )
      .toEqual([
        {
          progress: 1,
          savePath: '/downloads/Bangumi/Tiny Show/Season 1',
        },
      ]);
    expect(completedTorrent).toBeDefined();
    expect(completedTorrent).toMatchObject({
      num_leechs: 0,
      num_seeds: 0,
      tracker: '',
    });
    expect(
      completedTorrent!.tags
        .split(',')
        .map((tag) => tag.trim())
        .some((tag) => /^ab:\d+$/.test(tag))
    ).toBe(true);

    const peers = await (
      await expectStatus(
        await qb.get('/api/v2/sync/torrentPeers', {
          params: { hash: completedTorrent!.hash },
        })
      )
    ).json();
    expect(peers.peers ?? {}).toEqual({});
    const webSeeds = await (
      await expectStatus(
        await qb.get('/api/v2/torrents/webseeds', {
          params: { hash: completedTorrent!.hash },
        })
      )
    ).json();
    expect(webSeeds.map((seed: { url: string }) => seed.url)).toEqual([
      `${environment.mockInternalURL}/files/tiny-media.mkv`,
    ]);

    const renamedName = 'Tiny Show S01E01.mkv';
    const renamedPath = resolve(
      environment.downloadDirectory,
      'Bangumi',
      'Tiny Show',
      'Season 1',
      renamedName
    );
    await expect
      .poll(
        async () => {
          const files = (await (
            await expectStatus(
              await qb.get('/api/v2/torrents/files', {
                params: { hash: completedTorrent!.hash },
              })
            )
          ).json()) as QbFile[];
          return {
            disk: await fileState(renamedPath),
            files: files.map((file) => ({
              name: file.name,
              progress: file.progress,
              size: file.size,
            })),
          };
        },
        {
          intervals: [100, 250, 500, 1000],
          message: 'AutoBangumi should rename the completed qBittorrent file',
          timeout: 30_000,
        }
      )
      .toEqual({
        disk: {
          exists: true,
          sha256:
            '7daca2095d0438260fa849183dfc67faa459fdf4936e1bc91eec6b281b27e4c2',
          size: 65_536,
        },
        files: [{ name: renamedName, progress: 1, size: 65_536 }],
      });
    await expect
      .poll(
        async () => {
          const renamedTorrent = (await qbTorrents(qb))[0];
          return renamedTorrent?.tags
            .split(',')
            .map((tag) => tag.trim())
            .sort();
        },
        {
          intervals: [100, 250, 500],
          message: 'renamed qBittorrent task should receive completion tag',
          timeout: 10_000,
        }
      )
      .toEqual(
        expect.arrayContaining([
          'ab:renamed',
          expect.stringMatching(/^ab:\d+$/),
        ])
      );

    const upstreamJournal = await (
      await expectStatus(
        await request.get(`${environment.mockURL}/__admin/requests`)
      )
    ).json();
    const requestedPaths = upstreamJournal.requests.map(
      (entry: { path: string }) => entry.path
    );
    expect(requestedPaths).toEqual(
      expect.arrayContaining([
        '/rss/tiny-download.xml',
        '/torrents/tiny-media.torrent',
        '/files/tiny-media.mkv',
      ])
    );

    const bangumi = (await (
      await expectStatus(await request.get('/api/v1/bangumi/get/all'))
    ).json()) as BangumiRecord[];
    const tinyShow = bangumi.find(
      (item) => item.official_title === 'Tiny Show'
    );
    expect(tinyShow).toMatchObject({
      official_title: 'Tiny Show',
      save_path: '/downloads/Bangumi/Tiny Show/Season 1',
    });

    const rssItems = (await (
      await expectStatus(await request.get('/api/v1/rss'))
    ).json()) as RssRecord[];
    const storedRss = rssItems.find((item) => item.url === rss.url);
    expect(storedRss).toBeDefined();
    const storedTorrents = await (
      await expectStatus(
        await request.get(`/api/v1/bangumi/${tinyShow!.id}/torrents`)
      )
    ).json();
    expect(storedTorrents).toHaveLength(1);
    expect(storedTorrents[0]).toMatchObject({ downloaded: true });

    await expectStatus(
      await request.post(`/api/v1/rss/refresh/${storedRss!.id}`)
    );
    await expectStatus(
      await request.post(`/api/v1/rss/refresh/${storedRss!.id}`)
    );
    expect(await qbTorrents(qb)).toHaveLength(1);

    await page.goto('/#/downloader');
    const row = page
      .getByRole('row')
      .filter({ hasText: completedTorrent!.name });
    await expect(row).toBeVisible();
    await expect(row).toContainText('100%');

    await expectStatus(
      await request.delete(`/api/v1/bangumi/delete/${tinyShow!.id}`, {
        params: { file: 'true' },
      })
    );
    await expect
      .poll(() => qbTorrents(qb), {
        intervals: [100, 250, 500, 1000],
        message: 'qBittorrent task should be removed with its file',
        timeout: 15_000,
      })
      .toEqual([]);
    await expect
      .poll(() => fileState(renamedPath), {
        intervals: [100, 250, 500],
        message: 'shared renamed file should be removed',
        timeout: 10_000,
      })
      .toEqual({ exists: false, sha256: null, size: null });

    const remainingBangumi = (await (
      await expectStatus(await request.get('/api/v1/bangumi/get/all'))
    ).json()) as BangumiRecord[];
    expect(remainingBangumi.some((item) => item.id === tinyShow!.id)).toBe(
      false
    );
    expect(
      await (
        await expectStatus(
          await request.get(`/api/v1/bangumi/${tinyShow!.id}/torrents`)
        )
      ).json()
    ).toEqual([]);
  } finally {
    await qb.dispose();
  }
});
