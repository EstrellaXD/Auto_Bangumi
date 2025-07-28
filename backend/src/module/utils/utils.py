from datetime import datetime, timezone
from pickletools import read_string1
import time
import re


def extract_and_calculate_time_diff(text: str) -> float:
    """
    提取时间戳并计算与当前时间的差值
    正确处理UTC时区
    """
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    matches = re.findall(pattern, text)

    current_timestamp = time.time()
    current_dt = datetime.fromtimestamp(current_timestamp, tz=timezone.utc)

    for match in matches:
        try:
            # 解析为UTC datetime
            if match.endswith("Z"):
                dt = datetime.fromisoformat(match.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(match)

            # 确保有时区信息
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # 转换为UTC进行比较
            dt_utc = dt.astimezone(timezone.utc)

            # 计算差值
            time_diff = current_dt - dt_utc
            seconds_diff = time_diff.total_seconds()

        except Exception as e:
            print(f"解析失败 {match}: {e}")

    return seconds_diff
