export type AuthError = 'Not authenticated';

export type LoginError = 'Password error' | 'User not found';

export type ApiErrorMessage = AuthError | LoginError;

export interface ApiError {
  status: 401 | 404 | 422 | 500;
  detail: ApiErrorMessage;
}
