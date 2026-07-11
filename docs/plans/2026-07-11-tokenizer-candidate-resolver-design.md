# Tokenizer Candidate/Resolver 与 ParsedRelease 迁移设计

日期：2026-07-11  
状态：已确认，按 A（解析架构）→ B（业务迁移）实施

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
3. 标题只从最终获胜候选的 span 之外重建。
4. 默认 API 保持轻量，同时提供可选 `ParseTrace` 用于诊断。
5. `TitleParser`、RSS 偏好去重和 OffsetScanner 直接消费 `ParsedRelease`。
6. 保留 `raw_parser() -> Episode | None` 兼容接口，避免一次性迁移全部调用方。
7. 将手工语料矩阵持久化，并增加冲突、不变量和鲁棒性测试。

## 非目标

- 本轮不新增数据库表来持久化 PV、OP/ED 或 Batch。
- 本轮不让下载器自动下载所有可解析资源；由明确策略判断是否可消费。
- 不引入外部 anime parser 或 parser-combinator 依赖。
- 不以性能优化为目标；当前解析速度约为 110 微秒/标题。

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

核心类型：

```python
@dataclass(frozen=True, slots=True)
class Span:
    start: int
    end: int

@dataclass(frozen=True, slots=True)
class Candidate:
    rule_id: str
    field: ParseField
    value: object
    span: Span
    priority: int
    consume: bool = True
    segment_index: int | None = None

@dataclass(frozen=True, slots=True)
class Decision:
    candidate: Candidate
    accepted: bool
    reason: str

@dataclass(frozen=True, slots=True)
class ParseTrace:
    normalized: str
    candidates: tuple[Candidate, ...]
    decisions: tuple[Decision, ...]
    residual: str
    warnings: tuple[str, ...]
```

Resolver 使用稳定排序：字段策略 → priority → specificity → span 长度 → 原文位置。
单值字段只接受一个主候选；codec/audio 等多值字段接受所有不冲突候选；
重叠候选必须记录拒绝原因。相同优先级但不同值时产生 warning，不静默覆盖。

模块边界：

- `scanner.py`：Segment、Span 和括号扫描。
- `candidates.py`：Candidate、Decision、ParseTrace、ParseField。
- `rules/`：structural、media、technical、group 规则。
- `resolver.py`：统一冲突与 span 消费策略。
- `titles.py`：残余文本和标题片段重建。
- `parser.py`：只负责编排并构造 `ParsedRelease`。

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
- RSS preference dedup：键改为 `(bangumi_id, media_type, episode)`，缺少可用序号时跳过。
- OffsetScanner：仅消费 `MediaType.EPISODE`、`ReleaseKind.SINGLE` 和正整数集数。
- `raw_parser()`：继续作为未迁移调用方的兼容适配器。

## 测试策略

1. `release_title_golden.json` 持久化跨 Mikan、DMHY、Nyaa、Emby、Plex 的资源名。
2. Golden 测试对核心字段做精确快照，不再只断言标题包含某个片段。
3. 冲突测试覆盖 group/metadata、Movie 保留字、年份标题、多集数候选和重叠 span。
4. Metamorphic 测试验证：
   - 技术标签增删或重排不改变标题、季、集；
   - 等价括号布局不改变语义；
   - 添加 group 不改变媒体类型；
   - 所有 accepted span 均合法且互不冲突。
5. 无新依赖的确定性 fuzz：固定随机种子生成 Unicode、括号和未知标签，保证不抛异常。
6. 下游测试验证 range/PV 不进入单集去重，OVA 不污染 Offset，Movie 的 LLM/确定性投影一致。

## 迁移与回滚

先以现有 parser 结果作为 characterization 基线，实现 Candidate/Resolver 后跑全量
golden 对比。B 阶段保留 legacy adapter，任何未迁移消费者都可回退旧接口。
新业务策略通过小函数集中表达，不把策略重新写进解析器。

验收标准：全量 pytest、Ruff、Mypy 通过；golden corpus 无未解释差异；
ParseTrace 对每个被消费 span 都能指出 rule 和接受原因。
