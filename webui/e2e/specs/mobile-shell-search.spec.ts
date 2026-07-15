import type { Page } from '@playwright/test';

import type { BangumiAPI } from '../../types/bangumi';
import { expect, test } from '../fixtures/test';

// Mobile shell regression coverage for #1066/#1069. The keyboard/editor
// scenario remains in mobile-rule-editor.spec.ts; this file covers navigation.
const SEARCH_RESULTS = [
  {
    added: false,
    deleted: false,
    archived: false,
    dpi: '1920x1080',
    eps_collect: false,
    filter: '720|480',
    group_name: 'Fixture Group A',
    id: 0,
    official_title: 'Mobile Search Fixture',
    episode_offset: 0,
    season_offset: 0,
    poster_link: null,
    rss_link: '/rss/mobile-search-a.xml',
    rule_name: 'mobile-search-a',
    save_path: '',
    season: 1,
    season_raw: 'S1',
    source: null,
    subtitle: 'CHS',
    title_raw: 'Mobile Search Fixture A',
    year: '2026',
    air_weekday: null,
    weekday_locked: false,
    needs_review: false,
    needs_review_reason: null,
    preferred_group: null,
    preferred_resolution: null,
    episode_type: 'episode',
  },
  {
    added: false,
    deleted: false,
    archived: false,
    dpi: '1280x720',
    eps_collect: false,
    filter: '1080',
    group_name: 'Fixture Group B',
    id: 0,
    official_title: 'Mobile Search Fixture',
    episode_offset: 0,
    season_offset: 0,
    poster_link: null,
    rss_link: '/rss/mobile-search-b.xml',
    rule_name: 'mobile-search-b',
    save_path: '',
    season: 2,
    season_raw: 'S2',
    source: null,
    subtitle: 'CHT',
    title_raw: 'Mobile Search Fixture B',
    year: '2026',
    air_weekday: null,
    weekday_locked: false,
    needs_review: false,
    needs_review_reason: null,
    preferred_group: null,
    preferred_resolution: null,
    episode_type: 'episode',
  },
] satisfies BangumiAPI[];

interface SearchEventSourceAudit {
  closeCount: number;
  keywords: string;
  site: string;
}

async function installSearchEventSource(page: Page): Promise<void> {
  await page.addInitScript((results) => {
    const auditWindow = window as Window & {
      __searchEventSourceAudit?: SearchEventSourceAudit;
    };
    const NativeEventSource = window.EventSource;
    const audit: SearchEventSourceAudit = {
      closeCount: 0,
      keywords: '',
      site: '',
    };
    auditWindow.__searchEventSourceAudit = audit;

    class SearchEventSource extends EventTarget {
      readonly CONNECTING = 0;
      readonly OPEN = 1;
      readonly CLOSED = 2;
      readonly url: string;
      readonly withCredentials: boolean;
      readyState = this.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent<string>) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(url: string | URL, init?: EventSourceInit) {
        super();
        this.url = String(url);
        this.withCredentials = init?.withCredentials ?? false;
        const parsed = new URL(this.url, window.location.href);
        audit.keywords = parsed.searchParams.get('keywords') ?? '';
        audit.site = parsed.searchParams.get('site') ?? '';

        window.setTimeout(() => {
          if (this.readyState === this.CLOSED) return;
          this.readyState = this.OPEN;
          const openEvent = new Event('open');
          this.onopen?.(openEvent);
          this.dispatchEvent(openEvent);

          for (const result of results) {
            const message = new MessageEvent<string>('message', {
              data: JSON.stringify(result),
            });
            this.onmessage?.(message);
            this.dispatchEvent(message);
          }
        });
      }

      close(): void {
        if (this.readyState === this.CLOSED) return;
        this.readyState = this.CLOSED;
        audit.closeCount += 1;
      }
    }

    const RoutedEventSource = new Proxy(NativeEventSource, {
      construct(Target, argumentsList) {
        const [url, init] = argumentsList as [
          string | URL,
          EventSourceInit | undefined
        ];
        if (String(url).includes('api/v1/search/bangumi?')) {
          return new SearchEventSource(url, init);
        }
        return Reflect.construct(Target, argumentsList);
      },
    });

    Object.defineProperty(window, 'EventSource', {
      configurable: true,
      value: RoutedEventSource,
    });
  }, SEARCH_RESULTS);
}

async function installSearchFixture(page: Page): Promise<void> {
  await installSearchEventSource(page);
  await page.route('**/api/v1/search/provider', async (route) => {
    await route.fulfill({ json: ['mikan', 'nyaa'] });
  });
}

async function installOffsetMismatchFixture(page: Page): Promise<void> {
  await page.route('**/api/v1/bangumi/detect-offset', async (route) => {
    await route.fulfill({
      json: {
        has_mismatch: true,
        suggestion: {
          season_offset: 1,
          episode_offset: 0,
          reason: 'E2E offset mismatch',
          confidence: 'high',
        },
        tmdb_info: null,
      },
    });
  });
}

test('mobile shell routes without breakpoint redirects @mobile', async ({
  page,
}) => {
  expect(page.viewportSize()).toEqual({ width: 390, height: 844 });
  await page.goto('/#/');
  await expect(page).toHaveURL(/#\/home$/);
  await expect(
    page.locator('[data-summary="downloads"] [data-value="secondary"]')
  ).toHaveText('0 B/s');

  const navigation = page.getByRole('navigation', {
    name: 'Primary navigation',
  });
  await expect(navigation.getByRole('link', { name: 'Home' })).toBeVisible();
  await expect(navigation.getByRole('link', { name: 'Search' })).toBeVisible();
  await expect(
    navigation.getByRole('button', { name: 'More actions' })
  ).toContainText('More');

  await navigation.getByRole('link', { name: 'Search' }).click();
  await expect(page).toHaveURL(/#\/search$/);
  await expect(
    page.getByRole('region', { name: 'Search anime' })
  ).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);

  await page.setViewportSize({ width: 800, height: 844 });
  await expect(navigation).toBeHidden();
  await expect(page).toHaveURL(/#\/search$/);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(navigation).toBeVisible();
  await expect(page).toHaveURL(/#\/search$/);
});

test('mobile search preserves route, focus, and local state @mobile', async ({
  page,
}) => {
  await installSearchFixture(page);
  await page.goto('/#/search');

  const input = page.getByRole('textbox', { name: 'Search anime' });
  const provider = page.getByRole('button', {
    name: 'Select search provider',
  });
  await input.fill('Mobile Shell Fixture');

  await provider.click();
  await expect(page.getByRole('button', { name: 'nyaa' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'nyaa' })).toHaveCount(0);
  await expect(page).toHaveURL(/#\/search$/);
  await expect(input).toHaveValue('Mobile Shell Fixture');
  await expect(provider).toBeFocused();

  await provider.click();
  await page.getByRole('button', { name: 'nyaa' }).click();
  await expect(provider).toContainText('nyaa');
  await expect(provider).toBeFocused();

  await input.press('Enter');
  const groupFilter = page.getByRole('button', {
    name: 'Fixture Group A',
    exact: true,
  });
  await expect(groupFilter).toBeVisible();
  const observedSearch = await page.evaluate(
    () =>
      (
        window as Window & {
          __searchEventSourceAudit?: SearchEventSourceAudit;
        }
      ).__searchEventSourceAudit
  );
  expect(observedSearch).toMatchObject({
    keywords: 'Mobile Shell Fixture',
    site: 'nyaa',
  });
  await groupFilter.click();
  await expect(
    page.getByRole('button', { name: 'Clear Fixture Group A' })
  ).toBeVisible();

  const navigation = page.getByRole('navigation', {
    name: 'Primary navigation',
  });
  const closeCountBeforeNavigation = observedSearch?.closeCount ?? -1;
  expect(closeCountBeforeNavigation).toBe(0);
  await navigation.getByRole('link', { name: 'Home' }).click();
  await expect(page).toHaveURL(/#\/home$/);
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (
            window as Window & {
              __searchEventSourceAudit?: SearchEventSourceAudit;
            }
          ).__searchEventSourceAudit?.closeCount ?? -1
      )
    )
    .toBe(closeCountBeforeNavigation + 1);
  await navigation.getByRole('link', { name: 'Search' }).click();
  await expect(page).toHaveURL(/#\/search$/);

  await expect(input).toHaveValue('Mobile Shell Fixture');
  await expect(provider).toContainText('nyaa');
  await expect(
    page.getByRole('button', { name: 'Clear Fixture Group A' })
  ).toBeVisible();
});

test('mobile offset Escape returns to subscription confirmation @mobile', async ({
  page,
}) => {
  await installSearchFixture(page);
  await installOffsetMismatchFixture(page);
  await page.goto('/#/search');

  const input = page.getByRole('textbox', { name: 'Search anime' });
  await input.fill('Mobile Shell Fixture');
  await input.press('Enter');
  const variant = page.getByRole('button', {
    name: /Fixture Group A.*S1/,
  });
  await expect(variant).toBeVisible();
  await variant.click();

  const offsetDialog = page.getByRole('dialog', {
    name: 'Season/Episode Mismatch Detected',
  });
  await expect(
    offsetDialog.getByRole('button', { name: 'Keep Original' })
  ).toBeVisible();
  await page.keyboard.press('Escape');

  await expect(offsetDialog).toHaveCount(0);
  const confirmation = page.getByRole('dialog', {
    name: 'Add Subscription',
  });
  await expect(
    confirmation.getByRole('button', { name: 'Close' })
  ).toBeVisible();
  await expect(page).toHaveURL(/#\/search$/);
});

test('More hands off to one dialog and restores focus on cancel @mobile', async ({
  page,
}) => {
  await page.goto('/#/home');
  const navigation = page.getByRole('navigation', {
    name: 'Primary navigation',
  });
  const moreTrigger = navigation.getByRole('button', {
    name: 'More actions',
  });

  await moreTrigger.click();
  const moreDialog = page.getByRole('dialog', { name: 'More actions' });
  await expect(moreDialog.getByTestId('bottom-sheet-panel')).toBeVisible();
  await page.evaluate(() => {
    const auditWindow = window as Window & {
      __mobileDialogAudit?: {
        max: number;
        observer: MutationObserver;
      };
    };
    const countDialogs = () =>
      document.querySelectorAll('[role="dialog"]').length;
    const audit = {
      max: countDialogs(),
      observer: new MutationObserver(() => {
        audit.max = Math.max(audit.max, countDialogs());
      }),
    };
    audit.observer.observe(document.body, { childList: true, subtree: true });
    auditWindow.__mobileDialogAudit = audit;
  });

  await moreDialog.getByRole('button', { name: 'Logout' }).click();
  const confirmation = page.getByRole('dialog', {
    name: 'Log out of this account?',
  });
  await expect(confirmation.getByTestId('bottom-sheet-panel')).toBeVisible();
  await expect(moreDialog).toHaveCount(0);

  const maximumDialogCount = await page.evaluate(() => {
    const auditWindow = window as Window & {
      __mobileDialogAudit?: {
        max: number;
        observer: MutationObserver;
      };
    };
    const audit = auditWindow.__mobileDialogAudit;
    audit?.observer.disconnect();
    return audit?.max ?? 0;
  });
  expect(maximumDialogCount).toBe(1);

  await confirmation
    .getByRole('button', { name: 'Cancel', exact: true })
    .click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(moreTrigger).toBeFocused();
});
