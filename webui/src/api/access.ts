import type {
  ApiTokenCreated,
  ApiTokenPublic,
  TokenScope,
  UserCreate,
  UserPublic,
  UserUpdate,
} from '#/access';
import { axios } from '@/utils/axios';

export const apiUsers = {
  async list(): Promise<UserPublic[]> {
    const { data } = await axios.get<UserPublic[]>('api/v1/users');
    return data;
  },

  async create(payload: UserCreate): Promise<UserPublic> {
    const { data } = await axios.post<UserPublic>('api/v1/users', payload);
    return data;
  },

  async update(userId: number, payload: UserUpdate): Promise<UserPublic> {
    const { data } = await axios.patch<UserPublic>(
      `api/v1/users/${userId}`,
      payload
    );
    return data;
  },

  async delete(userId: number): Promise<void> {
    await axios.delete(`api/v1/users/${userId}`);
  },
};

export const apiTokens = {
  async list(): Promise<ApiTokenPublic[]> {
    const { data } = await axios.get<ApiTokenPublic[]>('api/v1/tokens');
    return data;
  },

  async create(name: string, scope: TokenScope): Promise<ApiTokenCreated> {
    const { data } = await axios.post<ApiTokenCreated>('api/v1/tokens', {
      name,
      scope,
    });
    return data;
  },

  async revoke(tokenId: number): Promise<void> {
    await axios.delete(`api/v1/tokens/${tokenId}`);
  },
};
