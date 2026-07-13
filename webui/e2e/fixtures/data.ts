export interface Credentials {
  username: string;
  password: string;
}

export interface SetupStatus {
  need_setup: boolean;
  version: string;
}

export interface UserPublic {
  id: number;
  username: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type TokenScope = 'api' | 'mcp';

export interface ApiTokenPublic {
  id: number;
  user_id: number;
  name: string;
  scope: TokenScope;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface ApiTokenCreated extends ApiTokenPublic {
  token: string;
}

export const SESSION_SUCCESS = { authenticated: true } as const;

export function changedPassword(prefix: string): string {
  return `${prefix}-Changed9!`;
}
