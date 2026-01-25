# Search Panel Redesign

## Overview

Redesign the search bar component from a dropdown list to a full modal-based search experience with advanced filtering capabilities.

## Problems with Current Implementation

1. **Click-outside clears everything** - `v-on-click-outside="clearSearch"` causes accidental loss of results
2. **Limited result display** - Absolute positioned list with no scroll container
3. **No explicit close control** - User has no intentional way to dismiss except clicking outside
4. **No filtering** - Results often contain same anime with different subtitle groups/seasons, hard to find the right one

## Design Goals

- Prevent accidental dismissal of search results
- Support displaying many results with proper scrolling
- Enable filtering by subtitle group, resolution, subtitle type, and season
- Provide confirmation step before subscribing

---

## Search Panel Structure

### Trigger & Toggle Behavior

- Clicking the search input opens the search modal (if closed) or closes it (if open)
- Pressing `Escape` closes the modal
- A visible `×` close button in the modal header provides explicit dismissal
- Clicking the backdrop does NOT close (prevents accidental loss of results)

### Modal Layout

```
┌─────────────────────────────────────────────────────────┐
│  🔍 [Search input]         [provider ▼]           [×]  │
├─────────────────────────────────────────────────────────┤
│ 字幕组:   [喵萌奶茶屋] [ANi] [桜都] [LoliHouse] [+3]    │
│ 分辨率:   [1080p] [720p] [4K]                          │
│ 字幕语言: [简中 CHS] [繁中 CHT] [双语] [内嵌] [外挂]     │
│ 季度:     [S1] [S2] [剧场版]                           │
│                                    [清除筛选] 8/24 结果 │
├─────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ Result  │ │ Result  │ │ Result  │                   │
│  │  Card   │ │  Card   │ │  Card   │                   │
│  └─────────┘ └─────────┘ └─────────┘                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ Result  │ │ Result  │ │ Result  │                   │
│  │  Card   │ │  Card   │ │  Card   │                   │
│  └─────────┘ └─────────┘ └─────────┘                   │
│                    (scrollable grid)                    │
└─────────────────────────────────────────────────────────┘
```

- Modal centered on screen with backdrop overlay
- Fixed header with search input, provider selector, close button
- Filter chips section below header (sticky when scrolling)
- Scrollable grid of result cards (3 columns on desktop, responsive)

---

## Filter Chip System

### Four Filter Dimensions

1. **字幕组 (Subtitle Group)** - Fansub team name
2. **分辨率 (Resolution)** - 720p, 1080p, 4K/2160p
3. **字幕语言 (Subtitle Type)** - CHS (简中), CHT (繁中), 双语 (Dual), 内嵌 (Hardcoded), 外挂 (External ASS/SRT)
4. **季度 (Season)** - S1, S2, Movie/剧场版, OVA

### Auto-generated Filters

- As results stream in, extract unique values for each dimension
- Chips appear dynamically as new filter values are discovered
- Parsing logic extracts metadata from torrent titles

### Filter Behavior

- Chips are toggleable - click to activate (highlighted), click again to deactivate
- Multiple filters can be active simultaneously
- Logic: AND within same category, OR across categories
- Active filters show with filled background, inactive with outline style
- "清除筛选" (Clear all) button appears when any filter is active
- Result count updates dynamically: "显示 8 / 24 个结果"

### Overflow Handling

- If a category has >5 options, show first 4 + `[+N more]` chip that expands
- Each category row can collapse/expand independently
- Collapsed state shows badge count for active filters

---

## Result Cards

### Card Design (Compact Grid Item)

```
┌──────────────────────────┐
│ ┌──────┐  葬送的芙莉莲   │
│ │poster│  Frieren        │
│ │      │  ─────────────  │
│ └──────┘  喵萌奶茶屋     │
│           1080p · 简中   │
│           S1 · 全28集    │
└──────────────────────────┘
```

### Card Content

- Thumbnail/poster (if available from API, placeholder if not)
- Title (Chinese + Romaji/English)
- Subtitle group badge
- Resolution + Subtitle type tags
- Season + Episode count

### Streaming Animation

- Cards fade in with slight upward slide (`opacity: 0 → 1`, `translateY: 8px → 0`)
- Staggered delay: each card delays 50ms after previous
- Grid re-flows smoothly as new cards appear
- Filter changes use same fade animation for showing/hiding

### Empty & Loading States

| State | Display |
|-------|---------|
| Initial | "输入关键词开始搜索" |
| Searching | Spinner in search input, cards stream in |
| No results | "未找到相关结果，试试其他关键词" |
| Filtered to zero | "没有符合筛选条件的结果" + "清除筛选" button |

---

## Confirmation Modal

When user clicks a result card, a nested modal appears for review before subscribing.

### Layout

```
┌─────────────────────────────────────────────────────┐
│  添加订阅                                      [×]  │
├─────────────────────────────────────────────────────┤
│  ┌────────┐                                         │
│  │        │  葬送的芙莉莲                           │
│  │ poster │  Sousou no Frieren                      │
│  │        │  ★ 9.2  ·  2023年秋  ·  全28集          │
│  └────────┘                                         │
├─────────────────────────────────────────────────────┤
│  RSS 源:    [当前选择的RSS链接]              [复制] │
│  字幕组:    喵萌奶茶屋                              │
│  分辨率:    1080p                                   │
│  字幕类型:  简体中文 (内嵌)                          │
├─────────────────────────────────────────────────────┤
│  高级设置 ▼                                         │
│  ┌─────────────────────────────────────────────┐   │
│  │ 过滤规则:  [自动生成的filter]                │   │
│  │ 保存路径:  /media/anime/葬送的芙莉莲/       │   │
│  │ 重命名:    ☑ 启用自动重命名                  │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│                          [取消]    [确认订阅 ✓]     │
└─────────────────────────────────────────────────────┘
```

### Behavior

- Shows parsed metadata for user review
- Advanced settings collapsed by default
- "确认订阅" adds to subscriptions and closes both modals
- "取消" returns to search results (results preserved)
- Escape key returns to search results (not full close)

---

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `Enter` (in search input) | Trigger search |
| `Escape` | Close confirmation modal (if open) → close search modal |
| `Tab` | Navigate through filter chips, then result cards |
| `Enter` (on focused card) | Open confirmation modal |
| Arrow keys | Navigate grid (optional enhancement) |

---

## Responsive Design

### Breakpoints

| Viewport | Grid | Modal Width | Behavior |
|----------|------|-------------|----------|
| Desktop (>1024px) | 3 columns | 800px centered | Full experience |
| Tablet (768-1024px) | 2 columns | 90% width | Filters collapse to single row |
| Mobile (<768px) | 1 column | Full screen | Bottom sheet style |

### Mobile Adaptations

- Modal becomes full-screen bottom sheet
- Filter chips horizontally scrollable (single row)
- Cards stack vertically (single column)
- Swipe down to close (in addition to × button)

---

## Component Structure

```
ab-search-modal.vue (new - main modal container)
├── ab-search-header.vue (search input + provider + close)
├── ab-search-filters.vue (new - filter chips)
├── ab-search-results.vue (new - scrollable grid)
│   └── ab-search-card.vue (new - individual result card)
└── ab-search-confirm.vue (new - confirmation modal)
```

### State Management

Extend `useSearchStore` with:
- `filters` - active filter state per dimension
- `filteredResults` - computed results after filter application
- `showModal` - modal open/close state
- `selectedResult` - currently selected result for confirmation

---

## Implementation Notes

### Filter Parsing

Need to extract metadata from torrent titles. Common patterns:
- Subtitle group: `[喵萌奶茶屋]`, `【ANi】`
- Resolution: `1080p`, `720p`, `2160p`, `4K`
- Subtitle type: `简体`, `繁體`, `CHS`, `CHT`, `简日双语`, `内嵌`, `外挂`
- Season: `S01`, `Season 1`, `第一季`, `剧场版`, `Movie`, `OVA`

### SSE Streaming

Keep existing SSE implementation but:
- Parse metadata from each result as it arrives
- Update filter options incrementally
- Apply active filters to new results immediately

### Animation

Use Vue's `<TransitionGroup>` with staggered delays:
```css
.card-enter-active {
  transition: all 0.3s ease;
  transition-delay: calc(var(--index) * 50ms);
}
.card-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
```
