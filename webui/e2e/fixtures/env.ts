import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const fixtureDirectory = fileURLToPath(new URL('.', import.meta.url));

export interface E2EEnvironment {
  baseURL: string;
  mockURL: string;
  mockInternalURL: string;
  fakeQbURL: string;
  fakeQbInternalURL: string;
  realQbURL: string | null;
  realQbInternalURL: string | null;
  downloaderURL: string;
  downloaderUsername: string;
  downloaderPassword: string;
  username: string;
  password: string;
  artifactDirectory: string;
  downloadDirectory: string;
  profile: 'browser' | 'downloader';
}

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value)
    throw new Error(`${name} must be set by the hermetic stack runner`);
  return value.replace(/\/$/, '');
}

function optional(name: string): string | null {
  const value = process.env[name]?.trim();
  return value ? value.replace(/\/$/, '') : null;
}

export function getE2EEnvironment(): E2EEnvironment {
  const profile = process.env.AB_E2E_PROFILE ?? 'browser';
  if (profile !== 'browser' && profile !== 'downloader')
    throw new Error(`Unsupported AB_E2E_PROFILE: ${profile}`);

  const fakeQbURL = required('AB_E2E_FAKE_QB_URL');
  const fakeQbInternalURL = required('AB_E2E_FAKE_QB_INTERNAL_URL');
  const realQbURL = optional('AB_E2E_QB_URL');
  const realQbInternalURL = optional('AB_E2E_QB_INTERNAL_URL');
  if (profile === 'downloader' && (!realQbURL || !realQbInternalURL))
    throw new Error(
      'AB_E2E_QB_URL and AB_E2E_QB_INTERNAL_URL are required for downloader profile'
    );

  return {
    baseURL: required('AB_E2E_BASE_URL'),
    mockURL: required('AB_E2E_MOCK_URL'),
    mockInternalURL: required('AB_E2E_MOCK_INTERNAL_URL'),
    fakeQbURL,
    fakeQbInternalURL,
    realQbURL,
    realQbInternalURL,
    downloaderURL:
      profile === 'downloader' ? realQbInternalURL! : fakeQbInternalURL,
    downloaderUsername: process.env.AB_E2E_QB_USERNAME?.trim() || 'admin',
    downloaderPassword: process.env.AB_E2E_QB_PASSWORD?.trim() || 'adminadmin',
    username: required('AB_E2E_USERNAME'),
    password: required('AB_E2E_PASSWORD'),
    artifactDirectory: resolve(required('AB_E2E_ARTIFACT_DIR')),
    downloadDirectory: resolve(required('AB_E2E_DOWNLOAD_DIR')),
    profile,
  };
}

export function authStatePath(browser: string): string {
  const profile = process.env.AB_E2E_PROFILE ?? 'browser';
  return resolve(fixtureDirectory, `../.auth/${profile}-${browser}.json`);
}
