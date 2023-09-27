import asyncio
import logging

import openai

DEFAULT_PROMPT = """\
You will now play the role of a super assistant. 
Your task is to extract structured data from unstructured text content and output it in JSON format. 
If you are unable to extract any information, please leave the field empty. Do not fabricate data!

the python structured data type is:

```python
@dataclass
class Episode:
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
```

Example:

```
input: "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
output: '{"group": "喵萌奶茶屋", "title_en": "Summer Time Rendering", "resolution": "1080p", "episode": 11, "season": 1}'

input: "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
output: '{"group": "幻樱字幕组", "title_en": "Komi-san wa, Komyushou Desu.", "resolution": "1920X1080", "episode": 22, "season": 2}'

input: "[Lilith-Raws] 关于我在无意间被隔壁的天使变成废柴这件事 / Otonari no Tenshi-sama - 09 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
output: '{"group": "Lilith-Raws", "title_en": "Otonari no Tenshi-sama", "resolution": "1080p", "episode": 9, "season": 1}'
```
"""


class OpenAIParser:
    def __init__(
        self,
        api_key: str,
        api_base: str | None = None,
        model: str | None = None,
        **kwargs,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")

        self._api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"
        self.model = model or "gpt-3.5-turbo"
        self.openai_kwargs = kwargs

    def parse(self, text: str, prompt: str | None = None) -> str:
        if not prompt:
            prompt = DEFAULT_PROMPT

        async def complete() -> str:
            resp = await openai.ChatCompletion.acreate(
                api_key=self._api_key,
                api_base=self.api_base,
                model=self.model,
                messages=[
                    dict(role="system", content=prompt),
                    dict(role="user", content=text),
                ],
                # set temperature to 0 to make results be more stable and reproducible.
                temperature=0,
                **self.openai_kwargs,
            )

            result = resp["choices"][0]["message"]["content"]
            return result

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(complete())

        logging.debug(f"the parsed result is: {result}")

        return result
