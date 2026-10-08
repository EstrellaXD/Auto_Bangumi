"""重命名策略：由媒体文件信息生成目标文件名。

注意：这里的 title/bangumi_name 来自已存在于磁盘上的文件/文件夹名（单个路径
分量，不可能含分隔符），不做保留字符清洗——追加清洗会让既有做种库（如含 ":"
的标题）在升级后被整库批量重命名 (#721 评审)。

电影/剧场版：Title (Year).ext，不使用 SxxExx 编号。bangumi_name 由调用方传入，
与 gen_save_path 的文件夹命名保持一致 (Title (Year))。
"""

from ab_sdk.rename import RenameInput, pad

NO_RENAME = "none"


class NoRename:
    """``none``：保留原路径。"""

    def target_name(self, f: RenameInput) -> str:
        return f.media_path


def standard_name(base: str, f: RenameInput) -> str:
    """``{base} SxxEyy[.语言].ext``；电影为 ``{base}[.语言].ext``。"""
    language = f".{f.language}" if f.kind == "subtitle" else ""
    if f.episode_type == "movie":
        return f"{base}{language}{f.suffix}"
    return f"{base} S{pad(f.season)}E{pad(f.episode)}{language}{f.suffix}"


class PnRename:
    """``pn``：以文件名解析出的标题命名。"""

    def target_name(self, f: RenameInput) -> str:
        return standard_name(f.title, f)


class AdvanceRename:
    """``advance``：以番剧文件夹名命名。"""

    def target_name(self, f: RenameInput) -> str:
        return standard_name(f.bangumi_name, f)
