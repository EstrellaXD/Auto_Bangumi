export interface UserPublic {
  id: number;
  username: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  username: string;
  password: string;
}

export interface UserUpdate {
  username?: string;
  password?: string;
  enabled?: boolean;
}

export type TokenScope = 'api' | 'mcp';
export type ApiTokenStatus = 'active' | 'expired' | 'revoked';

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
