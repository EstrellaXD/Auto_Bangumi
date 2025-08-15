from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Program(BaseModel):
    # rss_time must be greater than 300,if less than 300,it will be set to 300
    rss_time: int = Field(default=900, description="Sleep time")
    webui_port: int = Field(default=7892, description="WebUI port")

    @model_validator(mode="after")
    def validate_rss_time(self) -> Self:
        self.rss_time = max(self.rss_time, 300)
        return self


class Downloader(BaseModel):
    type: str = Field(default="qbittorrent", description="Downloader type")
    path: str = Field(default="/downloads/Bangumi", description="Downloader path")
    host: str = Field(
        default="172.17.0.1:8080", alias="host", description="Downloader host"
    )
    ssl: bool = Field(default=False, description="Downloader ssl")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_host(self) -> Self:
        # 如果输入值没有以 http:// 或 https:// 开头，自动加上 http://
        if not self.host.startswith(("http://", "https://")):
            self.host = f"http://{self.host}"
        return self


class RSSParser(BaseModel):
    enable: bool = Field(default=True, description="Enable RSS parser")
    filter: list[str] = Field(default=["720", r"\d+-\d"], description="Filter")
    include: list[str] = Field(default=[], description="Include")
    language: str = "zh"
    mikan_custom_url: str = Field(default="mikanani.me", description="Mikan custom url")
    tmdb_api_key: str = Field(
        default="",
        description="TMDB API key, used for TMDB integration",
    )


class BangumiManage(BaseModel):
    enable: bool = Field(default=True, description="Enable bangumi manage")
    eps_complete: bool = Field(default=False, description="Enable eps complete")
    rename_method: str = Field(default="pn", description="Rename method")
    group_tag: bool = Field(default=False, description="Enable group tag")
    remove_bad_torrent: bool = Field(default=False, description="Remove bad torrent")


class Log(BaseModel):
    debug_enable: bool = Field(default=False, description="Enable debug")


class Proxy(BaseModel):
    enable: bool = Field(default=False, description="Enable proxy")
    type: str = Field(default="http", description="Proxy type")
    host: str = Field(default="", description="Proxy host")
    port: int = Field(default=0, description="Proxy port")
    username: str = Field(default="", alias="username", description="Proxy username")
    password: str = Field(default="", alias="password", description="Proxy password")


class Notification(BaseModel):
    enable: bool = Field(default=False, description="Enable notification")
    type: str = Field(default="telegram", description="Notification type")
    token: str = Field(default="", alias="token", description="Notification token")
    chat_id: str = Field(
        default="", alias="chat_id", description="Notification chat id"
    )


# class ExperimentalOpenAI(BaseModel):
#     enable: bool = Field(False, description="Enable experimental OpenAI")
#     api_key: str = Field("", description="OpenAI api key")
#     api_base: str = Field(
#         "https://api.openai.com/v1", description="OpenAI api base url"
#     )
#     api_type: Literal["azure", "openai"] = Field(
#         "openai", description="OpenAI api type, usually for azure"
#     )
#     api_version: str = Field(
#         "2023-05-15", description="OpenAI api version, only for Azure"
#     )
#     model: str = Field(
#         "gpt-3.5-turbo", description="OpenAI model, ignored when api type is azure"
#     )
#     deployment_id: str = Field(
#         "", description="Azure OpenAI deployment id, ignored when api type is openai"
#     )


class Config(BaseModel):
    program: Program = Program()
    downloader: Downloader = Downloader()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()

    model_config = ConfigDict(extra="allow")

    # experimental_openai: ExperimentalOpenAI = ExperimentalOpenAI()
