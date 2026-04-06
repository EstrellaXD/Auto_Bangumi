# 种子管理入口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为番剧管理增加种子查看和删除能力，包括一个虚拟的 "Others" 入口展示孤儿种子。

**Architecture:** 后端在 bangumi API 下新增 6 个端点（orphans 在前避免路由冲突），数据库层新增 4 个方法。前端使用 file-based routing 创建种子列表页，复用一个 `ab-torrent-list` 组件。Others 作为虚拟 bangumi 卡片插入番剧列表。

**Tech Stack:** FastAPI, SQLModel/SQLite, Vue 3 + TypeScript, unplugin-vue-router, UnoCSS

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/src/module/database/torrent.py` | 新增 search_by_bangumi_id, search_orphans, delete_one, delete_orphans |
| Modify | `backend/src/module/api/bangumi.py` | 新增 6 个端点（import 加 Torrent, ResponseModel） |
| Modify | `webui/types/torrent.ts` | 扩展 Torrent 接口 |
| Modify | `webui/src/api/bangumi.ts` | 新增 6 个 API 函数 |
| Create | `webui/src/components/ab-torrent-list.vue` | 种子列表组件（两种页面复用） |
| Create | `webui/src/pages/index/bangumi/[id]/torrents.vue` | 番剧种子列表页 |
| Create | `webui/src/pages/index/bangumi/others/torrents.vue` | 孤儿种子列表页 |
| Modify | `webui/src/pages/index/bangumi.vue` | Others 卡片 |
| Modify | `webui/src/i18n/zh-CN.json` | 中文翻译 |
| Modify | `webui/src/i18n/en.json` | 英文翻译 |

---

### Task 1: 数据库层 — 新增 4 个方法

**Files:**
- Modify: `backend/src/module/database/torrent.py` (在 `update_qb_hash` 方法之后，第 103 行后)

- [ ] **Step 1: 添加 4 个方法**

```python
    def search_by_bangumi_id(self, bangumi_id: int) -> list[Torrent]:
        result = self.session.execute(
            select(Torrent).where(Torrent.bangumi_id == bangumi_id)
        )
        return list(result.scalars().all())

    def search_orphans(self) -> list[Torrent]:
        result = self.session.execute(
            select(Torrent).where(Torrent.bangumi_id == None)  # noqa: E711
        )
        return list(result.scalars().all())

    def delete_one(self, torrent_id: int) -> bool:
        torrent = self.search(torrent_id)
        if torrent is None:
            return False
        self.session.delete(torrent)
        self.session.commit()
        logger.debug("Deleted torrent %s.", torrent_id)
        return True

    def delete_orphans(self) -> int:
        result = self.session.execute(
            select(Torrent).where(Torrent.bangumi_id == None)  # noqa: E711
        )
        torrents = list(result.scalars().all())
        count = len(torrents)
        for t in torrents:
            self.session.delete(t)
        if count > 0:
            self.session.commit()
            logger.debug("Deleted %s orphan torrents.", count)
        return count
```

- [ ] **Step 2: 验证语法**

Run: `python3 -c "import py_compile; py_compile.compile('backend/src/module/database/torrent.py', doraise=True); print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add backend/src/module/database/torrent.py
git commit -m "feat(database): add torrent query and delete methods for management"
```

---

### Task 2: API 层 — 新增 6 个端点

**Files:**
- Modify: `backend/src/module/api/bangumi.py`

- [ ] **Step 1: 修改 import**

将第 10 行：
```python
from module.models import APIResponse, Bangumi, BangumiUpdate
```
改为：
```python
from module.models import APIResponse, Bangumi, BangumiUpdate, ResponseModel, Torrent
```

- [ ] **Step 2: 在文件末尾添加端点**

**路由注册顺序关键**：orphans 端点必须在 `{id}/torrents` 之前，否则 FastAPI 把字符串 `"torrents"` 当作 `{id}` 参数。

```python
# ── Torrent Management ──
# orphans 端点必须在 {id}/torrents 之前注册，避免路由冲突


@router.get(
    "/torrents/orphans",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def get_orphan_torrents():
    with TorrentManager() as manager:
        return manager.torrent.search_orphans()


@router.delete(
    "/torrents/orphans",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_orphan_torrents():
    with TorrentManager() as manager:
        count = manager.torrent.delete_orphans()
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted {count} orphan torrents.",
            msg_zh=f"已删除 {count} 条未匹配种子。",
        )
    )


@router.delete(
    "/torrents/orphans/{torrent_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_single_orphan_torrent(torrent_id: int):
    with TorrentManager() as manager:
        torrent = manager.torrent.search(torrent_id)
        if torrent is None or torrent.bangumi_id is not None:
            return u_response(
                ResponseModel(
                    status=False,
                    status_code=404,
                    msg_en=f"Orphan torrent {torrent_id} not found.",
                    msg_zh=f"未找到孤儿种子 {torrent_id}。",
                )
            )
        manager.torrent.delete_one(torrent_id)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted torrent {torrent_id}.",
            msg_zh=f"已删除种子 {torrent_id}。",
        )
    )


@router.get(
    "/{bangumi_id}/torrents",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def get_bangumi_torrents(bangumi_id: int):
    with TorrentManager() as manager:
        return manager.torrent.search_by_bangumi_id(bangumi_id)


@router.delete(
    "/{bangumi_id}/torrents",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_bangumi_torrents(bangumi_id: int):
    with TorrentManager() as manager:
        count = manager.torrent.delete_by_bangumi_id(bangumi_id)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted {count} torrents for bangumi {bangumi_id}.",
            msg_zh=f"已删除番剧 {bangumi_id} 的 {count} 条种子。",
        )
    )


@router.delete(
    "/{bangumi_id}/torrents/{torrent_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_single_torrent(bangumi_id: int, torrent_id: int):
    with TorrentManager() as manager:
        torrent = manager.torrent.search(torrent_id)
        if torrent is None or torrent.bangumi_id != bangumi_id:
            return u_response(
                ResponseModel(
                    status=False,
                    status_code=404,
                    msg_en=f"Torrent {torrent_id} not found under bangumi {bangumi_id}.",
                    msg_zh=f"番剧 {bangumi_id} 下未找到种子 {torrent_id}。",
                )
            )
        manager.torrent.delete_one(torrent_id)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted torrent {torrent_id}.",
            msg_zh=f"已删除种子 {torrent_id}。",
        )
    )
```

- [ ] **Step 3: 验证语法**

Run: `python3 -c "import py_compile; py_compile.compile('backend/src/module/api/bangumi.py', doraise=True); print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add backend/src/module/api/bangumi.py
git commit -m "feat(api): add torrent management endpoints for bangumi"
```

---

### Task 3: 前端类型和 API 函数

**Files:**
- Modify: `webui/types/torrent.ts`
- Modify: `webui/src/api/bangumi.ts`

- [ ] **Step 1: 扩展 Torrent 类型**

替换 `webui/types/torrent.ts` 全部内容：

```typescript
export interface Torrent {
  id: number;
  name: string;
  url: string;
  homepage: string | null;
  downloaded: boolean;
  bangumi_id: number | null;
  rss_id: number | null;
  qb_hash: string | null;
}
```

- [ ] **Step 2: 在 bangumi.ts 顶部添加 Torrent 类型导入**

在 `import type { ApiSuccess } from '#/api';` 后添加：

```typescript
import type { Torrent } from '#/torrent';
```

- [ ] **Step 3: 在 apiBangumi 对象末尾添加 6 个方法**

在 `getNeedsReview` 方法后添加：

```typescript
  // ── Torrent Management ──

  async getTorrents(bangumiId: number) {
    const { data } = await axios.get<Torrent[]>(
      `api/v1/bangumi/${bangumiId}/torrents`
    );
    return data;
  },

  async deleteAllTorrents(bangumiId: number) {
    const { data } = await axios.delete<ApiSuccess>(
      `api/v1/bangumi/${bangumiId}/torrents`
    );
    return data;
  },

  async deleteTorrent(bangumiId: number, torrentId: number) {
    const { data } = await axios.delete<ApiSuccess>(
      `api/v1/bangumi/${bangumiId}/torrents/${torrentId}`
    );
    return data;
  },

  async getOrphanTorrents() {
    const { data } = await axios.get<Torrent[]>(
      'api/v1/bangumi/torrents/orphans'
    );
    return data;
  },

  async deleteOrphanTorrents() {
    const { data } = await axios.delete<ApiSuccess>(
      'api/v1/bangumi/torrents/orphans'
    );
    return data;
  },

  async deleteOrphanTorrent(torrentId: number) {
    const { data } = await axios.delete<ApiSuccess>(
      `api/v1/bangumi/torrents/orphans/${torrentId}`
    );
    return data;
  },
```

- [ ] **Step 4: 验证前端编译**

Run: `cd webui && pnpm test:build`

- [ ] **Step 5: Commit**

```bash
git add webui/types/torrent.ts webui/src/api/bangumi.ts
git commit -m "feat(webui): add torrent management API functions and Torrent type"
```

---

### Task 4: 种子列表组件

**Files:**
- Create: `webui/src/components/ab-torrent-list.vue`

- [ ] **Step 1: 创建组件**

项目使用 `useApi` hook（`webui/src/hooks/useApi.ts`），接口为 `{ execute, isLoading }`。`execute` 直接传参数。`showMessage: true` 时自动显示后端返回的 `msg_zh/msg_en`。

```vue
<script setup lang="ts">
import { useApi } from '@/hooks/useApi';
import { apiBangumi } from '@/api/bangumi';
import type { Torrent } from '#/torrent';

const props = defineProps<{
  torrents: Torrent[];
  bangumiId?: number;
  isOrphan?: boolean;
}>();

const emit = defineEmits<{
  (e: 'deleted'): void;
}>();

const { execute: execDeleteOne, isLoading: deletingOne } = useApi(
  async (torrentId: number) => {
    if (props.isOrphan) {
      return apiBangumi.deleteOrphanTorrent(torrentId);
    }
    return apiBangumi.deleteTorrent(props.bangumiId!, torrentId);
  },
  {
    showMessage: true,
    onSuccess: () => emit('deleted'),
  }
);

const { execute: execDeleteAll, isLoading: deletingAll } = useApi(
  async () => {
    if (props.isOrphan) {
      return apiBangumi.deleteOrphanTorrents();
    }
    return apiBangumi.deleteAllTorrents(props.bangumiId!);
  },
  {
    showMessage: true,
    onSuccess: () => emit('deleted'),
  }
);
</script>

<template>
  <div class="torrent-list">
    <div v-if="torrents.length === 0" class="torrent-empty">
      {{ $t('bangumi.torrents.empty') }}
    </div>
    <div v-for="torrent in torrents" :key="torrent.id" class="torrent-item">
      <div class="torrent-info">
        <span class="torrent-name">{{ torrent.name }}</span>
        <div class="torrent-badges">
          <span v-if="torrent.downloaded" class="badge badge-downloaded">
            {{ $t('bangumi.torrents.downloaded') }}
          </span>
          <span v-if="torrent.rss_id" class="badge badge-rss">RSS</span>
          <span v-else class="badge badge-manual">
            {{ $t('bangumi.torrents.source.manual') }}
          </span>
        </div>
      </div>
      <button
        class="btn-delete"
        :disabled="deletingOne"
        @click="execDeleteOne(torrent.id)"
      >
        {{ $t('bangumi.torrents.delete') }}
      </button>
    </div>
    <div v-if="torrents.length > 0" class="torrent-actions">
      <button
        class="btn-delete-all"
        :disabled="deletingAll"
        @click="execDeleteAll()"
      >
        {{ $t('bangumi.torrents.deleteAll') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.torrent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.torrent-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
}

.torrent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--bg-secondary);
}

.torrent-info {
  flex: 1;
  min-width: 0;
}

.torrent-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.torrent-badges {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
}

.badge-downloaded { background: #4caf50; color: white; }
.badge-rss { background: #2196f3; color: white; }
.badge-manual { background: #ff9800; color: white; }

.btn-delete {
  font-size: 12px;
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  background: #f44336;
  color: white;
  cursor: pointer;
  flex-shrink: 0;
  margin-left: 8px;
}

.btn-delete:disabled { opacity: 0.5; }

.torrent-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}

.btn-delete-all {
  font-size: 13px;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: #f44336;
  color: white;
  cursor: pointer;
}

.btn-delete-all:disabled { opacity: 0.5; }
</style>
```

> **实现注意**：CSS 变量名（如 `--bg-secondary`、`--text-secondary`）需要参考项目实际使用的变量。如果 UnoCSS 是主要样式方案，可能需要改用 UnoCSS class。实现时读取现有组件的样式来匹配。

- [ ] **Step 2: Commit**

```bash
git add webui/src/components/ab-torrent-list.vue
git commit -m "feat(webui): add torrent list component"
```

---

### Task 5: 种子列表页面

**Files:**
- Create: `webui/src/pages/index/bangumi/[id]/torrents.vue`
- Create: `webui/src/pages/index/bangumi/others/torrents.vue`

项目使用 `unplugin-vue-router` file-based routing。创建页面文件即自动注册路由。

- [ ] **Step 1: 创建番剧种子列表页**

`webui/src/pages/index/bangumi/[id]/torrents.vue`：

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { apiBangumi } from '@/api/bangumi';
import AbTorrentList from '@/components/ab-torrent-list.vue';
import type { Torrent } from '#/torrent';

const route = useRoute();
const bangumiId = Number(route.params.id);
const torrents = ref<Torrent[]>([]);

async function load() {
  torrents.value = await apiBangumi.getTorrents(bangumiId);
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <h2>{{ $t('bangumi.torrents.title') }} #{{ bangumiId }}</h2>
    <AbTorrentList
      :torrents="torrents"
      :bangumi-id="bangumiId"
      @deleted="load"
    />
  </div>
</template>
```

- [ ] **Step 2: 创建孤儿种子列表页**

`webui/src/pages/index/bangumi/others/torrents.vue`：

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { apiBangumi } from '@/api/bangumi';
import AbTorrentList from '@/components/ab-torrent-list.vue';
import type { Torrent } from '#/torrent';

const torrents = ref<Torrent[]>([]);

async function load() {
  torrents.value = await apiBangumi.getOrphanTorrents();
}

onMounted(load);
</script>

<template>
  <div class="page-container">
    <h2>{{ $t('bangumi.others.title') }}</h2>
    <AbTorrentList
      :torrents="torrents"
      :is-orphan="true"
      @deleted="load"
    />
  </div>
</template>
```

- [ ] **Step 3: 验证编译**

Run: `cd webui && pnpm test:build`

- [ ] **Step 4: Commit**

```bash
git add webui/src/pages/index/bangumi/
git commit -m "feat(webui): add torrent list pages for bangumi and orphans"
```

---

### Task 6: Others 卡片

**Files:**
- Modify: `webui/src/pages/index/bangumi.vue`

> **注意**：此 task 需要读取 `bangumi.vue` 和 `ab-bangumi-card.vue` 的完整代码来确定插入位置和方式。以下为指导性描述。

- [ ] **Step 1: 读取 bangumi.vue 和 ab-bangumi-card.vue**

了解番剧列表的渲染逻辑和卡片组件的 props 接口。

- [ ] **Step 2: 添加孤儿数量状态**

在 bangumi.vue 的 `<script setup>` 中添加获取孤儿种子数量的逻辑：

```typescript
const orphanCount = ref(0);

async function loadOrphanCount() {
  const orphans = await apiBangumi.getOrphanTorrents();
  orphanCount.value = orphans.length;
}

onMounted(loadOrphanCount);
```

- [ ] **Step 3: 在番剧网格末尾添加 Others 卡片**

如果现有卡片组件 `ab-bangumi-card` 可以接收一个虚拟 bangumi 对象，则构造一个：

```typescript
const othersBangumi = computed(() => ({
  id: -1,
  official_title: 'Others',
  poster_link: null,
  // ... 其他必要字段用默认值填充
}));
```

在网格中最后一个卡片后渲染 Others 卡片，点击时 `router.push('/bangumi/others/torrents')`。

如果 `ab-bangumi-card` 的 props 要求太多必填字段，则单独渲染一个自定义卡片。

- [ ] **Step 4: Commit**

```bash
git add webui/src/pages/index/bangumi.vue
git commit -m "feat(webui): add Others card to bangumi list for orphan torrents"
```

---

### Task 7: i18n 翻译

**Files:**
- Modify: `webui/src/i18n/zh-CN.json`
- Modify: `webui/src/i18n/en.json`

- [ ] **Step 1: 读取现有 i18n 文件结构**

确认 key 的层级结构和格式。

- [ ] **Step 2: 在两个文件中添加翻译 key**

需要添加的 key（插入到 `bangumi` 或 `homepage` 节点下，按现有层级）：

| Key | zh-CN | en |
|-----|-------|-----|
| `bangumi.others.title` | 未匹配种子 | Others |
| `bangumi.torrents.title` | 种子列表 | Torrents |
| `bangumi.torrents.delete` | 删除 | Delete |
| `bangumi.torrents.deleteAll` | 清空所有 | Delete All |
| `bangumi.torrents.downloaded` | 已下载 | Downloaded |
| `bangumi.torrents.empty` | 暂无种子 | No torrents |
| `bangumi.torrents.source.manual` | 手动/订阅 | Manual |

- [ ] **Step 3: Commit**

```bash
git add webui/src/i18n/
git commit -m "feat(webui): add i18n keys for torrent management"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动后端，验证 API**

Run: `cd backend/src && uv run python main.py`

验证端点（需带认证 token）：
- `GET /api/v1/bangumi/torrents/orphans` — 返回孤儿种子列表
- `GET /api/v1/bangumi/1/torrents` — 返回番剧 1 的种子
- `DELETE /api/v1/bangumi/torrents/orphans/{torrent_id}` — 删除单条孤儿

- [ ] **Step 2: 启动前端，验证页面**

Run: `cd webui && pnpm dev`

- 番剧列表页显示 Others 卡片
- 点击跳转到 `/bangumi/others/torrents`，显示孤儿种子
- 删除功能正常

- [ ] **Step 3: 修复问题并提交**

```bash
git add -A
git commit -m "fix: address e2e testing issues"
```
