import re
import logging
from os import path


logger = logging.getLogger(__name__)

class EPParser:
    def __init__(self):
        self.rules = [
            r"(.*)\[(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
            r"(.*)\[E(\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)?\](.*)",
            r"(.*)\[第(\d*\.*\d*)话(?:END)?\](.*)",
            r"(.*)\[第(\d*\.*\d*)話(?:END)?\](.*)",
            r"(.*)第(\d*\.*\d*)话(?:END)?(.*)",
            r"(.*)第(\d*\.*\d*)話(?:END)?(.*)",
            r"(.*)- (\d{1,3}|\d{1,3}\.\d{1,2})(?:v\d{1,2})?(?:END)? (.*)",
        ]

    def rename_normal(self, name):
        for rule in self.rules:
            matchObj = re.match(rule, name, re.I)
            if matchObj is not None:
                new_name = f"{matchObj.group(1).strip()} E{matchObj.group(2)}{matchObj.group(3)}"
                return new_name

    def rename_pn(self, name):
        n = re.split(r"[\[\]()【】（）]", name)
        file_name = name.replace(f"[{n[1]}]", "")
        for rule in self.rules:
            matchObj = re.match(rule, file_name, re.I)
            if matchObj is not None:
                new_name = re.sub(
                    r"[\[\]]",
                    "",
                    f"{matchObj.group(1).strip()} E{matchObj.group(2)}{path.splitext(name)[-1]}",
                )
                return new_name

    def rename_none(self, name):
        return name


if __name__ == "__main__":
    name = "[NC-Raws]间谍过家家 - 09(B-Global 3840x2160 HEVC AAC MKV).mkv"
    rename = EPParser()
    new_name = rename.rename_pn(name)
    print(new_name)