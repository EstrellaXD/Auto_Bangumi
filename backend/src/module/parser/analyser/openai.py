import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from pydantic import BaseModel
from typing import Optional

from openai import OpenAI, AzureOpenAI

from module.models import Bangumi

logger = logging.getLogger(__name__)

class Episode(BaseModel):
    title_en: Optional[str]
    title_zh: Optional[str]
    title_jp: Optional[str]
    season: str
    season_raw: str
    episode: str
    sub: str
    group: str
    resolution: str
    source: str


DEFAULT_PROMPT = """\
You will now play the role of a super assistant. 
Your task is to extract structured data from unstructured text content and output it in JSON format. 
If you are unable to extract any information, please keep all fields and leave the field empty or default value like `''`, `None`.
But Do not fabricate data!
"""


class OpenAIParser:
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_type: str = "openai",
        **kwargs,
    ) -> None:
        """OpenAIParser is a class to parse text with openai

        Args:
            api_key (str): the OpenAI api key
            api_base (str):
                the OpenAI api base url, you can use custom url here. \
                Defaults to "https://api.openai.com/v1".
            model (str):
                the ChatGPT model parameter, you can get more details from \
                https://platform.openai.com/docs/api-reference/chat/create. \
                Defaults to "gpt-4o-mini".
            kwargs (dict):
                the OpenAI ChatGPT parameters, you can get more details from \
                https://platform.openai.com/docs/api-reference/chat/create.

        Raises:
            ValueError: if api_key is not provided.
        """
        if not api_key:
            raise ValueError("API key is required.")
        if api_type == "azure":
            self.client = AzureOpenAI(
                api_key=api_key,
                base_url=api_base,
                azure_deployment=kwargs.get("deployment_id", ""),
                api_version=kwargs.get("api_version", "2023-05-15"),
            )
        else:
            self.client = OpenAI(api_key=api_key, base_url=api_base)

        self.model = model
        self.openai_kwargs = kwargs

    def parse(
        self, text: str, prompt: str | None = None, asdict: bool = True
    ) -> dict | str:
        """parse text with openai

        Args:
            text (str): the text to be parsed
            prompt (str | None, optional):
                the custom prompt. Built-in prompt will be used if no prompt is provided. \
                Defaults to None.
            asdict (bool, optional):
                whether to return the result as dict or not. \
                Defaults to True.

        Returns:
            dict | str: the parsed result.
        """
        if not prompt:
            prompt = DEFAULT_PROMPT

        params = self._prepare_params(text, prompt)

        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(self.client.beta.chat.completions.parse, **params)
            resp = future.result()

            result = resp.choices[0].message.parsed

        if asdict:
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                logger.warning(f"Cannot parse result {result} as python dict.")

        logger.debug(f"the parsed result is: {result}")

        return result

    def _prepare_params(self, text: str, prompt: str) -> dict[str, Any]:
        """_prepare_params is a helper function to prepare params for openai library.
        There are some differences between openai and azure openai api, so we need to
        prepare params for them.

        Args:
            text (str): the text to be parsed
            prompt (str): the custom prompt

        Returns:
            dict[str, Any]: the prepared key value pairs.
        """
        params = dict(
            model=self.model,
            messages=[
                dict(role="system", content=prompt),
                dict(role="user", content=text),
            ],
            response_format=Episode,

            # set temperature to 0 to make results be more stable and reproducible.
            temperature=0,
        )

        api_type = self.openai_kwargs.get("api_type", "openai")
        if api_type == "azure":
            params["deployment_id"] = self.openai_kwargs.get("deployment_id", "")
            params["api_version"] = self.openai_kwargs.get("api_version", "2023-05-15")
            params["api_type"] = "azure"
        else:
            params["model"] = self.model

        return params
