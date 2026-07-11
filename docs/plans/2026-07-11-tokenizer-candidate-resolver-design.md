# Tokenizer Candidate/Resolver 与 ParsedRelease 迁移设计

日期：2026-07-11  
状态：已实施，A（解析架构）与 B（业务迁移）均已完成

## 背景

当前 tokenizer 已能解析普通剧集、半集、范围、合集、Movie、OVA/OAD、
PV、NCOP/NCED 及无集数标题，并通过现有回归和跨来源资源名矩阵。
但 `parser.py` 仍采用“规则匹配后立即 mask，再按执行顺序修改 State”的方式。
低优先级规则一旦消费 span，后续规则无法恢复原文；不同字段的冲突策略也不一致。

另一方面，业务主链路仍通过兼容层把 `ParsedRelease` 压缩成旧 `Episode`。
范围、批量、PV、半集等信息因此被拒绝或丢失。解析能力和业务能力需要分层，
不能继续用 `None` 同时表示“无法解析”和“业务暂不处理”。

## 目标

1. 规则只负责产生不可变候选，不直接修改最终状态或消费文本。
2. Resolver 统一处理优先级、重叠、冲突、接受和拒绝原因。
3. 标题只从 Resolver 明确标记为 `Decision.excluded_spans` 的范围之外重建；
   SHADOWED metadata 可排除自身 marker，但不会排除依赖其获胜才成立的标题范围。
4. 默认 API 保持轻量，同时提供可选 `ParseTrace` 用于诊断。
5. `TitleParser`、RSS 偏好去重和 OffsetScanner 直接消费 `ParsedRelease`。
6. 保留 `raw_parser() -> Episode | None` 兼容接口，避免一次性迁移全部调用方。
7. 将手工语料矩阵持久化，并增加冲突、不变量和鲁棒性测试。

## 非目标

- 本轮不新增数据库表来持久化 PV、OP/ED 或 Batch。
- 本轮不让下载器自动下载所有可解析资源；由明确策略判断是否可消费。
- 不引入外部 anime parser 或 parser-combinator 依赖。
- 不以性能优化为目标；71 条 golden corpus 本机基准约为 150 微秒/标题，开启
  完整 trace 约为 164 微秒/标题（约 9% 额外开销）。

## A：Candidate → Resolver → Trace

解析流程改为：

```text
normalize
  → scan segments/spans
  → rules emit Candidate[]
  → resolver accepts/rejects candidates
  → reconstruct titles from unconsumed spans
  → ParsedRelease + optional ParseTrace
```

当前数据流：

```mermaid
flowchart LR
    Raw[资源名称] --> Normalize[normalize + segment scan]
    Normalize --> Rules[group / structural / media / technical collectors]
    Rules --> Observations[Observation + atomic Candidate]
    Observations --> Resolver[stable Resolver]
    Resolver --> Resolution[Claims + Decisions + excluded spans]
    Resolution --> Titles[residual title reconstruction]
    Titles --> Parsed[ParsedRelease]
    Resolution -. optional diagnostics .-> Trace[ParseTrace]

    Parsed --> Policy[release_policy]
    Policy --> TitleParser[TitleParser: Bangumi / Movie / reject]
    Policy --> RSS[RSS typed preference dedup]
    Policy --> Offset[Offset: positive integer weekly episode only]
    Parsed --> Legacy[legacy adapter: Episode | None]
```

核心类型：

```python
@dataclass(frozen=True, slots=True)
class Span:
    segment: int
    start: int
    end: int

@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    rule_id: str
    spans: tuple[Span, ...]
    claims: Claims
    priority: int
    specificity: int = 0
    conflict_tags: frozenset[str] = frozenset()
    blocks: frozenset[str] = frozenset()

@dataclass(frozen=True, slots=True)
class Decision:
    candidate_id: str
    status: DecisionStatus
    reason: str

@dataclass(frozen=True, slots=True)
class ParseTrace:
    normalized: str
    observations: tuple[Observation, ...]
    candidates: tuple[Candidate, ...]
    claims: Claims
    decisions: tuple[Decision, ...]
    excluded_spans: tuple[Span, ...]
    residuals: tuple[str, ...]
    warnings: tuple[ResolutionWarning, ...]
```

Resolver 使用稳定排序：priority → specificity → segment/span → rule id → candidate id。
单值字段只接受一个主候选；codec/audio 等多值字段接受所有不冲突候选；原子
Claims 保证 `S02E05`、`OVA01`、range 不会被拆成互相矛盾的半份结果。重叠候选
记录 `SHADOWED / REJECTED_AS_TITLE / REJECTED_CONFLICT` 原因；相同优先级但
不同值时产生 warning，不静默覆盖。

实际模块边界：

- `candidate.py`：Span、Observation、原子 Claims、Candidate 与 Decision。
- `resolver.py`：稳定排序、字段冲突、显式 block、重叠 span、warning 与最终 Claims。
- `trace.py`：ParseTrace、TraceSegment 与可选的 ParseOutcome。
- `parser.py`：括号扫描、group/structural/media/technical 候选收集、标题重建与编排。
- `result.py`：稳定的 ParsedRelease、MediaType 与 ReleaseKind 公共领域模型。
- `release_policy.py`：持久化、偏好去重和 Offset 的业务准入策略。

规则收集目前仍集中在 `parser.py`，这是刻意保留的后续模块化优化点；冲突解析和
业务策略已经从该文件中分离，不再依赖规则执行顺序修改 `_State`。

## B：业务链路迁移

确定性解析路径直接返回并消费 `ParsedRelease`。LLM 结果先归一化成同一模型，
随后统一投影到 `Bangumi` 或 `Movie`，消除“确定性 Movie 进 Movie 表、LLM Movie
却进 Bangumi 表”的差异。

业务策略和解析成功分离：

| 资源 | 解析 | TitleParser 投影 | RSS 集数去重 | Offset |
|---|---|---|---|---|
| 普通整数集 | 接受 | Bangumi | 参与 | 参与 |
| 半集 | 接受 | Bangumi | 使用数值键参与 | 不参与季度偏移 |
| Movie | 接受 | Movie | 不参与剧集去重 | 不参与 |
| OVA/OAD/SP | 接受 | Bangumi special | 使用类型+序号键 | 不参与 |
| Range/Batch/Collection | 接受 | 由策略决定，默认不自动新增 | 不参与单集去重 | 不参与 |
| PV/OP/ED | 接受 | 默认不持久化 | 不参与 | 不参与 |
| 纯标题 | 接受 | 默认不自动新增 | 不参与 | 不参与 |

迁移调用点：

- `TitleParser.raw_parser()`：确定性路径直接调用 `parse_release_title()`。
- RSS preference dedup：键改为
  `(bangumi_id, media_type, normalized_season, episode)`，并以
  `(preference_score, revision)` 排序；缺少安全单集身份时跳过去重。
- OffsetScanner：仅消费 `MediaType.EPISODE`、`ReleaseKind.SINGLE` 和正整数集数。
- `raw_parser()`：继续作为未迁移调用方的兼容适配器。

## 测试策略

1. `release_title_golden.json` 持久化 71 个跨 Mikan、DMHY、Nyaa、Emby、Plex 的资源名。
2. Golden 测试对核心字段做精确快照，不再只断言标题包含某个片段。
3. 冲突测试覆盖 group/metadata、Movie 保留字、年份标题、多集数候选和重叠 span。
4. Metamorphic 测试验证：
   - 技术标签增删或重排不改变标题、季、集；
   - 等价括号布局不改变语义；
   - 添加 group 不改变媒体类型；
   - 所有 excluded span 均合法且可归因；exclusive winners 不互相重叠，
     `OverlapPolicy.SHARED` overlay 是明确例外。
5. 无新依赖的确定性性质矩阵：448 个固定随机种子/变形场景覆盖 Unicode、括号、
   技术标签和未知标签，保证确定性与不抛异常。
6. 下游测试验证 range/PV 不进入单集去重，OVA 不污染 Offset，Movie 的 LLM/确定性投影一致。

## 性能基准

Tokenizer benchmark 是纯标准库 CLI，不引入 `pytest-benchmark`，也不在普通测试或
CI 中设置机器相关的速度阈值：

```bash
cd backend

# 71 条真实语料；分别测 plain、Trace 和 Trace 开销
uv run python scripts/benchmark_tokenizer.py

# 加入固定 stress 语料，并保存可复算的原始样本
uv run python scripts/benchmark_tokenizer.py \
  --suite all --format json --output tokenizer-benchmark.json

# 只检查 benchmark 流程，不作为有效性能数据
uv run python scripts/benchmark_tokenizer.py \
  --suite all --warmup-rounds 1 --samples 1 --loops 1
```

默认先 warm up 20 轮，再为每个分组自动校准 loops，使每个 sample 至少持续 250ms，
最后采集 7 个 sample。主指标是每个资源名的 median，辅助报告 p95、MAD、吞吐量和
完整 `sample_elapsed_ns`。真实语料划分为 episode、cardinality、media、ambiguous、
technical；stress 套件单独观察 1/4/16/64 个技术标签以及冲突 marker，避免合成输入
污染真实语料总分。

比较两次结果时至少要核对 Python、平台、commit、worktree dirty 状态和 corpus
SHA-256。Plain 与 Trace 的结果一致性在计时区外验证；语料加载、GC collect、报告
序列化和输出均不计入样本时间。

## 迁移与回滚

先以现有 parser 结果作为 characterization 基线，实现 Candidate/Resolver 后跑全量
golden 对比。B 阶段保留 legacy adapter，任何未迁移消费者都可回退旧接口。
新业务策略通过小函数集中表达，不把策略重新写进解析器。

验收标准：全量 pytest、Ruff、Mypy 通过；golden corpus 无未解释差异；
ParseTrace 对每个被消费 span 都能指出 rule 和接受原因。
