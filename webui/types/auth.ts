export interface SessionSuccess {
  authenticated: true;
}

export type Update = SessionSuccess;

export interface User {
  username: string;
  password: string;
}
