# vulture 白名单：这里登记的名字被确认为「不是死代码」，按原因分组。
# 新增条目前先确认它确实有用；真正的死代码应当删除而不是加进来。
# ruff: noqa
# type: ignore
_ = object()

# --- pydantic / SQLModel 字段：经序列化（API 响应、数据库列）使用 ---
suggested_offset
total_seasons
has_mismatch
created
connected
message_zh
message_en
family
item_count
last_seen_at
needs_review_reason
_.needs_review_reason
backup_state
new_revision
model_config
published_at
is_prerelease
applied_version
can_rollback
_.applied_version
_.can_rollback
phase
percent
candidate_ids
credentials
can_query
can_rename
can_manage
can_rss_rules

# --- 协议 / 回调签名要求的参数 ---
connection_record  # SQLAlchemy connect 事件回调
exc_value  # __aexit__
traceback  # __aexit__
user_input  # LLMProviderAdapter.complete_auth 的接口参数
hash_  # for 循环解包

# --- 框架回调 ---
_.dispatch  # Starlette BaseHTTPMiddleware

# --- 测试 / e2e 支撑：生产路径不调用 ---
_.check_single  # e2e worker
_.set_renamed_path  # aria2 测试构造状态
_.add_mock_torrent  # MockDownloader 测试辅助
_.get_state  # MockDownloader 测试辅助
_reset_client_cache  # conftest
create_tables  # 同步建表，迁移测试使用
clear_network_cache  # 测试隔离 lru_cache
_.contains  # tokenizer Span API，测试覆盖
_.decision_for  # tokenizer trace API，测试覆盖
load_corpus  # tokenizer 基准测试工具
run_benchmark
render_text

# --- 插件运行时（module/plugin）---
# 公开接口：宿主在 P2/P3 迁移扩展点时调用（声明扩展点、执行 transform 钩子）
_.declare
_.transform
_.runner
_.drain  # 等待事件处理完，测试与关闭流程使用
# 插件通过 ctx 访问的能力、清单与注册表的数据字段
_.kv
authors
factory
# 动态创建插件包时设置的模块属性
_.__path__
_.__package__

# --- P3 ingest ---
# 内置插件：由插件加载器按 plugin.toml 的 entry 导入，钩子经 @hook 扫描登记
IngestFilters
_.include_regex

# --- P4 organize ---
# 内置插件：由插件管理器按 plugin.toml 加载，经 @provider / @subscribe 注册
TemplateRename
MediaServerRefresh
_.on_file_renamed
