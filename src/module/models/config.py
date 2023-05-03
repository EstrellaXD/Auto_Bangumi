from pydantic import BaseModel, Field

# Sub config


class Program(BaseModel):
    sleep_time: int = Field(7200, description="Sleep time")
    rename_times: int = Field(20, description="Rename times in one loop")
    webui_port: int = Field(7892, description="WebUI port")


class Downloader(BaseModel):
    type: str = Field("qbittorrent", description="Downloader type")
    host: str = Field("172.17.0.1:8080", description="Downloader host")
    username: str = Field("admin", description="Downloader username")
    password: str = Field("adminadmin", description="Downloader password")
    path: str = Field("/downloads/Bangumi", description="Downloader path")
    ssl: bool = Field(False, description="Downloader ssl")


class RSSParser(BaseModel):
    enable: bool = Field(True, description="Enable RSS parser")
    type: str = Field("mikan", description="RSS parser type")
    token: str = Field("token", description="RSS parser token")
    custom_url: str = Field("mikanime.tv", description="Custom RSS host url")
    enable_tmdb: bool = Field(False, description="Enable TMDB")
    filter: list[str] = Field(["720", r"\d+-\d"], description="Filter")
    language: str = "zh"


class BangumiManage(BaseModel):
    enable: bool = Field(True, description="Enable bangumi manage")
    eps_complete: bool = Field(False, description="Enable eps complete")
    rename_method: str = Field("pn", description="Rename method")
    group_tag: bool = Field(False, description="Enable group tag")
    remove_bad_torrent: bool = Field(False, description="Remove bad torrent")


class Log(BaseModel):
    debug_enable: bool = Field(False, description="Enable debug")


class Proxy(BaseModel):
    enable: bool = Field(False, description="Enable proxy")
    type: str = Field("http", description="Proxy type")
    host: str = Field("", description="Proxy host")
    port: int = Field(0, description="Proxy port")
    username: str = Field("", description="Proxy username")
    password: str = Field("", description="Proxy password")


class Notification(BaseModel):
    enable: bool = Field(False, description="Enable notification")
    type: str = Field("telegram", description="Notification type")
    token: str = Field("", description="Notification token")
    chat_id: str = Field("", description="Notification chat id")


class Config(BaseModel):
    data_version: float = Field(5.0, description="Data version")
    program: Program = Program()
    downloader: Downloader = Downloader()
    rss_parser: RSSParser = RSSParser()
    bangumi_manage: BangumiManage = BangumiManage()
    log: Log = Log()
    proxy: Proxy = Proxy()
    notification: Notification = Notification()
