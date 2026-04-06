# mikan_parser 修复设计

> 日期: 2026-04-06
> 上游 spec: .claude/.superpowers/2026-04-06-修复RSS无法添加种子/spec.md (Section 5.1)

---

## 问题

`mikan_parser.py` 有 4 个 crash 点，任何网络超时或页面结构变化都会导致 `AttributeError`：
1. `get_html()` 返回 None → `BeautifulSoup(None)` → 后续 `.find()` 返回 None → `.get("style")` crash
2. `soup.find("div", {"class": "bangumi-poster"})` 返回 None → `.get("style")` crash
3. `soup.select_one(...)` 返回 None → `.text` crash
4. 失败结果 `("", "")` 被缓存到 `_mikan_cache` → 永久失败

上层 `analyser.py` 捕获 `AttributeError` 后静默 pass，bangumi 以降级标题创建。但因为 `_mikan_cache` 缓存了空值，下次 `rss_loop` 不再重试 → **一次网络超时导致永久降级**。

另外，`official_title_parser` 中 `bangumi.official_title = official_title` 会把 raw_parser 设好的降级标题覆盖为空字符串。

## 方案

### 修改 1：mikan_parser.py — None 安全 + 不缓存失败

逐步检查每个可能返回 None 的操作，每个失败点记录含 homepage URL 的 warning 日志。

**具体改动：**

```python
async def mikan_parser(homepage: str) -> tuple[str, str]:
    if homepage in _mikan_cache:
        return _mikan_cache[homepage]
    root_path = parse_url(homepage).host
    async with RequestContent() as req:
        content = await req.get_html(homepage)
        if not content:
            logger.warning("[Mikan] Failed to fetch homepage: %s", homepage)
            return ("", "")
        soup = BeautifulSoup(content, "html.parser")

        poster_link = ""
        poster_div = soup.find("div", {"class": "bangumi-poster"})
        if poster_div is None:
            logger.warning("[Mikan] No poster div found on: %s", homepage)
        else:
            poster_style = poster_div.get("style")
            if poster_style:
                poster_path = poster_style.split("url('")[1].split("')")[0]
                poster_path = poster_path.split("?")[0]
                img = await req.get_content(f"https://{root_path}{poster_path}")
                if img:
                    suffix = poster_path.split(".")[-1]
                    poster_link = save_image(img, suffix)
                else:
                    logger.warning("[Mikan] Failed to download poster from: %s", homepage)
            else:
                logger.warning("[Mikan] Poster div has no style attribute on: %s", homepage)

        official_title = ""
        title_elem = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if title_elem is None:
            logger.warning("[Mikan] No official title found on: %s", homepage)
        else:
            official_title = re.sub(r"第.*季", "", title_elem.text).strip()

        # 只缓存成功结果
        if poster_link and official_title:
            _mikan_cache[homepage] = (poster_link, official_title)
        return (poster_link, official_title)
```

### 修改 2：analyser.py — 不覆盖降级值

`official_title_parser` 中，只在 mikan_parser 返回非空值时才覆盖 bangumi 的字段：

```python
async def official_title_parser(self, bangumi, rss, torrent):
    if rss.parser == "mikan":
        try:
            poster_link, official_title = await self.mikan_parser(torrent.homepage)
            if official_title:
                bangumi.official_title = official_title
            if poster_link:
                bangumi.poster_link = poster_link
        except AttributeError:
            logger.warning("[Parser] Mikan torrent has no homepage info.")
    elif rss.parser == "tmdb":
        ...
```

**保留外层 try/except AttributeError** 作为防御层——虽然修复后不应触发，但防御式编程是合理的。

## 影响分析

### 行为变更对比

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 网络超时 | crash → catch → bangumi 以 raw_parser 标题创建 → **缓存空值 → 永久降级** | 返回 `("", "")` → bangumi **保留** raw_parser 标题 → **不缓存 → 下次重试** |
| 海报 div 不存在 | crash → 标题也无法提取 | 跳过海报，**继续提取标题** |
| 标题元素不存在 | crash → catch → bangumi 以 raw_parser 标题创建 | 返回空标题 → bangumi **保留** raw_parser 标题 |
| 全部成功 | 正常缓存 | 行为不变 |

### 上层影响

- `analyser.py:official_title_parser` — 不再触发 AttributeError catch，但保留的 catch 不会有副作用
- `analyser.py:torrents_to_data` — bangumi.official_title 不再被覆盖为空字符串，保留 raw_parser 的降级值
- `sub_thread.py:rss_loop` — 行为不变，下一次 loop 会重新调用 mikan_parser（因为不缓存了）

### 其他 Parser

- `tmdb_parser` — 已有 None 检查，缓存 None 是因为查不到而非临时故障，合理。不需要改。
- `bgm_parser` — 结构简单，已有 None 检查。不需要改。

## 修改清单

| 文件 | 改动 | 行数 |
|------|------|------|
| `backend/src/module/parser/analyser/mikan_parser.py` | None 安全 + 不缓存失败 | ~30 行改动 |
| `backend/src/module/rss/analyser.py` | official_title_parser 不覆盖降级值 | ~5 行改动 |

不涉及数据库、API、前端。
