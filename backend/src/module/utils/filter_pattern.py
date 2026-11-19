"""排除过滤词编译为正则。"""

import logging
import re
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def compile_filter(terms: Iterable[str], flags: int = 0) -> re.Pattern[str] | None:
    """把排除过滤词编译成一个交替正则；没有有效过滤词时返回 ``None``（不排除）。

    空白过滤词会被丢掉：``"720|"`` 里的空分支能匹配任何标题，会把所有种子都排除。
    这种空项很容易出现，例如设置里多留了一个空行、规则 filter 末尾多一个逗号。
    整体不是合法正则时退回按字面匹配每个过滤词。
    """
    kept = [t for t in terms if t and t.strip()]
    if not kept:
        return None
    try:
        return re.compile("|".join(kept), flags)
    except re.error:
        logger.warning("过滤词 %s 不是合法正则，改为按字面匹配", kept)
        return re.compile("|".join(re.escape(t) for t in kept), flags)
