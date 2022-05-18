import re

import requests

name = "[IET字幕组][闪电十一人 FF篇][01][1080P][WebRip][繁日双语][AVC AAC][MP4]"
split_rule = r"\[|\]|\【|\】|\★|\（|\）|\(|\)"
n = re.split(split_rule, name)
while '' in n:
    n.remove('')
print(n)