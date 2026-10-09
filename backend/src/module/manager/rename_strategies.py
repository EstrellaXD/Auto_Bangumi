"""宿主自带的重命名方式 ``none``：保留原路径。

``pn`` / ``advance`` / ``template`` 由内置插件 ``rename`` 提供
（module/plugins/builtin/rename/）。
"""

from ab_sdk.rename import RenameInput

NO_RENAME = "none"


class NoRename:
    def target_name(self, f: RenameInput) -> str:
        return f.media_path
