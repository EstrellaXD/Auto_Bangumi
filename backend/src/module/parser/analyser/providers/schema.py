"""LLM 解析的共享输出契约：Episode 形状、JSON schema 与提示词。

物理上从 llm.py 抽出以打破 llm ↔ providers 的循环导入；llm.py 原地
重导出这些名字，外部 import 路径（含测试）保持不变。
"""

from typing import Any, Optional

from pydantic import BaseModel


class Episode(BaseModel):
    """LLM 结构化输出的目标形状（与 models.bangumi.Episode 字段一致）。"""

    title_en: Optional[str]
    title_zh: Optional[str]
    title_jp: Optional[str]
    season: int
    season_raw: str
    episode: int
    sub: str
    group: str
    resolution: str
    source: str


# Anthropic 结构化输出要求：所有属性均列入 required，
# additionalProperties 为 false，且不带 min/max 等约束
EPISODE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_en": {"type": ["string", "null"]},
        "title_zh": {"type": ["string", "null"]},
        "title_jp": {"type": ["string", "null"]},
        "season": {"type": "integer"},
        "season_raw": {"type": "string"},
        "episode": {"type": "integer"},
        "sub": {"type": "string"},
        "group": {"type": "string"},
        "resolution": {"type": "string"},
        "source": {"type": "string"},
    },
    "required": [
        "title_en",
        "title_zh",
        "title_jp",
        "season",
        "season_raw",
        "episode",
        "sub",
        "group",
        "resolution",
        "source",
    ],
    "additionalProperties": False,
}


DEFAULT_PROMPT = """\
You will now play the role of a super assistant.
Your task is to extract structured data from unstructured text content and output it in JSON format.
If you are unable to extract any information, please keep all fields and leave the field empty or default value like `''`, `None`.
But Do not fabricate data!
"""

# Gemini 走 response_mime_type + 提示词描述 JSON 形状（避免 SDK schema
# 类型与 mypy 冲突），因此在提示词里显式给出字段列表
GEMINI_JSON_INSTRUCTION = (
    "Output a single JSON object with exactly these keys: "
    "title_en (string or null), title_zh (string or null), "
    "title_jp (string or null), season (integer), season_raw (string), "
    "episode (integer), sub (string), group (string), "
    "resolution (string), source (string)."
)
