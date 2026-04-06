# 种子管理入口设计

> 日期: 2026-04-06
> 上游 spec: .claude/.superpowers/2026-04-06-修复RSS无法添加种子/spec.md (Section 5.2)

---

## 背景

torrent 表是高频故障表（8 个相关 issue 中 4 个直接涉及）。当前 84% 的种子记录（353/419）是孤儿——没有关联的 bangumi 记录。用户无法查看或清理这些数据。

核心问题：
- 无法查看某番剧下有哪些种子
- 无法删除单条种子记录（让 refresh_rss 重新处理）
- 无法清理孤儿种子

## 方案

### 后端 API 设计

采用混合策略：正常番剧的种子管理挂在 bangumi 接口下，孤儿种子用独立端点。

#### 新增端点

> **路由注册顺序**：orphans 端点必须在 `{id}/torrents` 之前注册。
> FastAPI 按注册顺序匹配，如果 `{id}/torrents` 先注册，`"torrents"` 会被当作 `id` 参数导致 404。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/bangumi/torrents/orphans` | GET | 获取孤儿种子列表 |
| `/api/v1/bangumi/torrents/orphans` | DELETE | 清理所有孤儿种子 |
| `/api/v1/bangumi/{id}/torrents` | GET | 获取某番剧下的种子列表 |
| `/api/v1/bangumi/{id}/torrents` | DELETE | 清空该番剧下所有种子 |
| `/api/v1/bangumi/{id}/torrents/{torrent_id}` | DELETE | 删除单条种子 |

#### 为什么不用 id=-1 复用？

删除 bangumi 时有级联逻辑（删 RSS → 删种子 → 删 bangumi 记录 → 可选删文件）。要复用 `DELETE /bangumi/delete/{id}` 就得大改 delete_rule，风险高且不必要。独立端点更清晰。

#### 为什么种子端点挂在 bangumi 下而不是顶层 /torrents/？

种子的消费场景是"番剧管理"——用户查看某部番的种子、清理某部番的种子。挂在 bangumi 下符合用户心智模型。

### 数据库层（`torrent.py`）

新增方法：

```python
def search_by_bangumi_id(self, bangumi_id: int) -> list[Torrent]:
    """查询某番剧下的所有种子"""

def search_orphans(self) -> list[Torrent]:
    """查询 bangumi_id IS NULL 的孤儿种子"""

def delete_one(self, torrent_id: int) -> bool:
    """删除单条种子记录，返回是否成功。
    torrent_id 不存在时返回 False。"""

def delete_orphans(self) -> int:
    """删除所有孤儿种子，返回删除数量"""
```

> **归属校验**：`DELETE /{id}/torrents/{torrent_id}` 需要校验 `torrent.bangumi_id == id`，
> 防止通过一个番剧的端点删除另一个番剧的种子。不匹配时返回 404。

已有 `delete_by_bangumi_id(bangumi_id)` 可直接复用于清空某番下所有种子。

### 前端设计

#### 番剧列表页 Others 卡片

在番剧列表末尾添加一个特殊的 "Others" 卡片：
- 复用现有番剧卡片组件的视觉结构
- 标题："Others" / "未匹配种子"
- 副标题：显示孤儿种子数量 badge
- 无海报，使用占位图标
- 点击后**路由跳转**到 `/bangumi/others/torrents`（独立页面，非内联展开）

#### 种子列表页（`/bangumi/others/torrents` 或 `/bangumi/{id}/torrents`）

独立路由页面，复用同一个种子列表组件。

每个种子项显示：
- 种子名称
- 匹配状态（已匹配 / 孤儿）
- 下载状态（downloaded badge）
- 来源（有 rss_id → "RSS"；无 rss_id → "手动/订阅"）
- 删除按钮

底部有"清理所有"按钮，带确认对话框。

> **不需要分页**——当前最多几百条种子记录，一次性加载即可。如果未来数据量增大再加。

#### 前端 API 调用（`webui/src/api/bangumi.ts` 新增）

```typescript
getTorrents(bangumiId: number): Promise<Torrent[]>
deleteTorrent(bangumiId: number, torrentId: number): Promise<APIResponse>
deleteAllTorrents(bangumiId: number): Promise<APIResponse>
getOrphanTorrents(): Promise<Torrent[]>
deleteOrphanTorrents(): Promise<APIResponse>
```

#### 前端 Torrent 类型扩展（`webui/types/torrent.ts`）

现有 `Torrent` 接口缺少 `bangumi_id` 和 `rss_id` 字段，需要补充：

```typescript
export interface Torrent {
  id: number;
  name: string;
  url: string;
  homepage: string | null;
  downloaded: boolean;
  bangumi_id: number | null;  // 新增：匹配状态
  rss_id: number | null;       // 新增：来源
  qb_hash: string | null;
}
```

#### API 响应格式

所有 API 使用项目现有的 `ResponseModel` 统一格式：
- 列表端点：`{"status": true, "data": [...]}`
- 删除端点：`{"status": true, "msg_en": "...", "msg_zh": "Deleted N records"}`
- 资源不存在：`{"status": false, "status_code": 404, "msg_en": "...", "msg_zh": "..."}`
- 无孤儿种子时：返回空列表 `[]`，不报错

#### i18n 新增 key

```
bangumi.others.title       — "Others" / "未匹配种子"
bangumi.torrents.delete    — "Delete" / "删除"
bangumi.torrents.deleteAll — "Delete All" / "清空所有"
bangumi.torrents.confirmDelete — "Are you sure?" / "确认删除？"
bangumi.torrents.orphanCount — "{count} orphan torrents" / "{count} 条未匹配种子"
bangumi.torrents.source.rss — "RSS" / "RSS"
bangumi.torrents.source.manual — "Manual" / "手动/订阅"
```

### 删除行为说明

所有删除操作**只删数据库记录，不删下载器中的实际文件**。

删除后效果：
- `refresh_rss` 的 `check_new` 不再过滤这些种子 URL
- 种子被重新拉取和处理（如果还在 RSS feed 中）
- 这是用户"重试"的主要方式

### 诊断功能

不需要独立入口。种子列表本身就是最好的诊断 UI：

| 信息 | 展示方式 |
|------|---------|
| 匹配状态 | 种子列表中显示 bangumi_id 是否存在 |
| 下载状态 | downloaded 字段的 badge |
| 来源 | rss_id 是否存在 |
| 匹配失败原因 | 问题 1 的增强日志已覆盖 |

## 修改清单

| 文件 | 改动 |
|------|------|
| `backend/src/module/database/torrent.py` | 新增 search_by_bangumi_id, search_orphans, delete_one, delete_orphans |
| `backend/src/module/api/bangumi.py` | 新增 5 个端点（orphans 在前，{id} 在后） |
| `webui/src/api/bangumi.ts` | 新增 5 个 API 调用函数 |
| `webui/src/types/torrent.ts` | 扩展 Torrent 接口，添加 bangumi_id, rss_id |
| `webui/src/pages/` 或 `webui/src/components/` | Others 卡片 + 种子列表页组件 |
| `webui/src/i18n/` | 新增翻译 key |
| `webui/src/router/` | 新增 /bangumi/others/torrents 路由 |

## 不涉及

- 不修改现有 delete_rule 的级联逻辑（删番剧仍自动删种子）
- 不修改 refresh_rss 的匹配逻辑
- 不创建实际的 "Others" bangumi 数据库记录
- 删除种子时不删下载器中的实际文件
- 删除种子时不删关联的 bangumi 记录

## 路由注册顺序

FastAPI 按注册顺序匹配。orphans 端点**必须**在 `{id}/torrents` 之前注册，否则 FastAPI 会把字符串 `"torrents"` 解析为 `{id}` 参数：

```python
# 正确顺序
router.get("/torrents/orphans", ...)   # 先注册
router.get("/{id}/torrents", ...)      # 后注册
```
