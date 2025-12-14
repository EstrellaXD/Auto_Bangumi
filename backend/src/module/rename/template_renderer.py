import re
from typing import Any


class TemplateRenderer:
    """
    模板渲染器，用于处理自定义重命名模板

    规则：
    1. 没有的参数要忽略（从模板中移除）
    2. 当使用 ${torrent_name} 时，忽略其他所有参数，直接使用种子原名
    3. 除了 torrent_name 外，其他参数都需要加上 suffix 后缀
    """

    @staticmethod
    def render_template(template: str, params: dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            template: 模板字符串，如 "${name} S${season}E${episode}${group}"
            params: 参数字典，包含所有可用的参数

        Returns:
            渲染后的文件名
        """
        if not template or not isinstance(template, str):
            return ""

        # 1. 检查是否包含 torrent_name
        if "${torrent_name}" in template:
            torrent_name = params.get("torrent_name", "")
            suffix = params.get("suffix", "")
            torrent_name += suffix
            return torrent_name

        # 2. 替换存在的参数，忽略不存在的参数
        result = template

        # 找到所有模板参数
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, result)

        for param_name in matches:
            param_value = params.get(param_name)
            placeholder = f"${{{param_name}}}"

            if param_value is not None and param_value != "":
                # 对于数字参数进行格式化
                if param_name in ["season", "episode"] and isinstance(param_value, (int, str)):
                    try:
                        param_value = f"{int(param_value):02d}"
                    except (ValueError, TypeError):
                        param_value = str(param_value)

                result = result.replace(placeholder, str(param_value))
            else:
                # 移除空参数及其可能的前缀空格或分隔符
                result = result.replace(placeholder, "")

        # 3. 清理多余的空格和分隔符
        result = re.sub(r"\s+", " ", result)  # 多个空格合并为一个
        result = result.strip()  # 移除首尾空格

        # 4. 自动添加 suffix 后缀（如果还没有）
        suffix = params.get("suffix", "")
        if suffix and not result.endswith(suffix):
            result += suffix

        return result

    @staticmethod
    def get_available_params(
        file_info,
        bangumi_name: str,
    ) -> dict[str, Any]:
        """
        收集所有可用的模板参数

        Args:
            file_info: EpisodeFile 或 SubtitleFile 对象
            bangumi_name: 番剧名称
            torrent_name: 种子原始名称

        Returns:
            参数字典
        """
        season = getattr(file_info, "season", 1)
        episode = getattr(file_info, "episode", 0)
        params = {
            "torrent_name": getattr(file_info, "torrent_name", ""),
            "official_title": bangumi_name,
            "title": getattr(file_info, "title_raw", ""),
            "season": f"{season:02d}",
            "episode": f"{episode:02d}",
            "suffix": getattr(file_info, "suffix", ""),
            "title": getattr(file_info, "title", ""),
            "group": getattr(file_info, "group", ""),
            "resolution": getattr(file_info, "resolution", ""),
            "source": getattr(file_info, "source", ""),
            "year": getattr(file_info, "year", ""),
        }

        # 对于字幕文件，添加语言参数
        if hasattr(file_info, "language"):
            params["language"] = getattr(file_info, "language", "")

        return params


if __name__ == "__main__":
    # 测试用例
    from module.parser import torrent_parser

    renderer = TemplateRenderer()
    title = "[LoliHouse] 2.5次元的诱惑  - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
    file_info = torrent_parser(title)
    print(file_info)

    params = renderer.get_available_params(file_info)

    # 测试1: 纯 torrent_name 模板
    template1 = "${torrent_name}"
    result1 = renderer.render_template(template1, params)
    print(f"测试1: {result1}")  # 应该输出: [字幕组] 番剧名称 第02话.mkv

    # 测试2: 标准参数组合（忽略空值）
    template2 = "${name} S${season}E${episode} - ${group}"
    template2 = "${title} S${season}E${episode} - ${group}"
    result2 = renderer.render_template(template2, params)
    print(f"测试2: {result2}")  # 应该输出: 番剧名称 S01E02.mkv

    # 测试3: 混合模板（torrent_name 优先）
    template3 = "${name} S${season}E${episode}${torrent_name}"
    result3 = renderer.render_template(template3, file_info.dict())
    print(f"测试3: {result3}")  # 应该输出: [字幕组] 番剧名称 第02话.mkv
