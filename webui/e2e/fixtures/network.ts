import type { Page, Response, TestInfo } from '@playwright/test';
import type { E2EEnvironment } from './env';

const MAX_RESPONSE_BODY = 4096;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function redactArtifact(
  value: string,
  environment: E2EEnvironment
): string {
  let redacted = value;
  const secrets = [
    environment.password,
    environment.downloaderPassword,
    process.env.AB_E2E_QB_PASSWORD ?? '',
  ].filter(Boolean);
  for (const secret of secrets)
    redacted = redacted.replace(
      new RegExp(escapeRegExp(secret), 'g'),
      '[REDACTED]'
    );

  return redacted
    .replace(/(Bearer\s+)[^\s"',]+/gi, '$1[REDACTED]')
    .replace(/ab_(?:api|mcp|session)_[A-Za-z0-9._~-]+/g, '[REDACTED]')
    .replace(
      /("?(?:password|token|authorization|cookie)"?\s*[:=]\s*)"?[^\s,"'}]+/gi,
      '$1[REDACTED]'
    );
}

interface FailedResponseArtifact {
  status: number;
  url: string;
  body: string;
}

export class NetworkGuard {
  private readonly allowedOrigins: Set<string>;
  private readonly blocked: string[] = [];
  private readonly consoleMessages: string[] = [];
  private readonly pageErrors: string[] = [];
  private readonly failedRequests: string[] = [];
  private readonly failedResponses: FailedResponseArtifact[] = [];
  private readonly pending = new Set<Promise<void>>();

  constructor(
    private readonly page: Page,
    private readonly environment: E2EEnvironment
  ) {
    this.allowedOrigins = new Set(
      [environment.baseURL, environment.mockURL].map(
        (value) => new URL(value).origin
      )
    );
  }

  private isAllowed(rawURL: string): boolean {
    const url = new URL(rawURL);
    if (url.protocol === 'ws:') url.protocol = 'http:';
    if (url.protocol === 'wss:') url.protocol = 'https:';
    if (url.protocol === 'http:' || url.protocol === 'https:')
      return this.allowedOrigins.has(url.origin);
    return ['about:', 'blob:', 'data:'].includes(url.protocol);
  }

  async install(): Promise<void> {
    const context = this.page.context();
    await context.route('**/*', async (route) => {
      const url = route.request().url();
      if (!this.isAllowed(url)) {
        this.blocked.push(url);
        await route.abort('blockedbyclient');
        return;
      }
      await route.continue();
    });
    await context.routeWebSocket('**/*', async (webSocket) => {
      const url = webSocket.url();
      if (!this.isAllowed(url)) {
        this.blocked.push(url);
        await webSocket.close({ code: 1008, reason: 'E2E network allowlist' });
        return;
      }
      webSocket.connectToServer();
    });

    this.page.on('console', (message) => {
      this.consoleMessages.push(`${message.type()}: ${message.text()}`);
    });
    this.page.on('pageerror', (error) => {
      this.pageErrors.push(error.stack ?? error.message);
    });
    this.page.on('requestfailed', (request) => {
      this.failedRequests.push(
        `${request.method()} ${request.url()}: ` +
          `${request.failure()?.errorText ?? 'unknown failure'}`
      );
    });
    this.page.on('response', (response) => {
      if (response.status() < 400) return;
      const capture = this.captureResponse(response).finally(() => {
        this.pending.delete(capture);
      });
      this.pending.add(capture);
    });
  }

  private async captureResponse(response: Response): Promise<void> {
    let body = '';
    try {
      body = (await response.text()).slice(0, MAX_RESPONSE_BODY);
    } catch {
      body = '[unavailable]';
    }
    this.failedResponses.push({
      status: response.status(),
      url: response.url(),
      body,
    });
  }

  async finish(testInfo: TestInfo): Promise<void> {
    await Promise.allSettled(this.pending);
    if (testInfo.status !== testInfo.expectedStatus) {
      const diagnostics = redactArtifact(
        JSON.stringify(
          {
            blocked: this.blocked,
            console: this.consoleMessages,
            pageErrors: this.pageErrors,
            failedRequests: this.failedRequests,
            failedResponses: this.failedResponses,
          },
          null,
          2
        ),
        this.environment
      );
      await testInfo.attach('browser-diagnostics.json', {
        body: diagnostics,
        contentType: 'application/json',
      });
    }

    if (this.blocked.length > 0) {
      const urls = this.blocked
        .map((url) => redactArtifact(url, this.environment))
        .join(', ');
      throw new Error(`Browser attempted public network access: ${urls}`);
    }
  }
}
