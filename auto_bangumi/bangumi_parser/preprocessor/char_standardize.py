replace_chars = {
    "【": "[",
    "】": "]",
    "：": ":",
    "【": "[",
    "】": "]",
    "-": "-",
    "（": "(",
    "）": ")",
    "＆": "&",
    "X": "x",
    "×": "x",
    "Ⅹ": "x",
    "__": "/",
    "\n": "",
}


class CharStandardize:
    def preprocess(self, name):
        # 替换中文字符
        for old, new in replace_chars.items():
            name = name.replace(old, new)
        return name
