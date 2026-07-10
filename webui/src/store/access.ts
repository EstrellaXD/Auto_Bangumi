import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { TokenScope, UserCreate, UserUpdate } from '#/access';
import { apiTokens, apiUsers } from '@/api/access';

export const useAccessStore = defineStore('access', () => {
  const users = ref<Awaited<ReturnType<typeof apiUsers.list>>>([]);
  const tokens = ref<Awaited<ReturnType<typeof apiTokens.list>>>([]);
  const loading = ref(false);

  async function load(): Promise<void> {
    loading.value = true;
    try {
      [users.value, tokens.value] = await Promise.all([
        apiUsers.list(),
        apiTokens.list(),
      ]);
    } finally {
      loading.value = false;
    }
  }

  async function createUser(payload: UserCreate): Promise<void> {
    await apiUsers.create(payload);
    users.value = await apiUsers.list();
  }

  async function updateUser(
    userId: number,
    payload: UserUpdate
  ): Promise<void> {
    await apiUsers.update(userId, payload);
    users.value = await apiUsers.list();
  }

  async function deleteUser(userId: number): Promise<void> {
    await apiUsers.delete(userId);
    users.value = await apiUsers.list();
  }

  async function createToken(name: string, scope: TokenScope): Promise<string> {
    const created = await apiTokens.create(name, scope);
    const { token, ...publicToken } = created;
    tokens.value = [
      publicToken,
      ...tokens.value.filter((item) => item.id !== publicToken.id),
    ];
    return token;
  }

  async function revokeToken(tokenId: number): Promise<void> {
    await apiTokens.revoke(tokenId);
    tokens.value = await apiTokens.list();
  }

  return {
    users,
    tokens,
    loading,
    load,
    createUser,
    updateUser,
    deleteUser,
    createToken,
    revokeToken,
  };
});
