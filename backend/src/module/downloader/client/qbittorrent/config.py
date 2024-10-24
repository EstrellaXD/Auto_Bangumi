from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_core.core_schema import ValidatorFunctionWrapHandler


class Config(BaseModel):
    type: str = Field(default="qbittorrent", description="Downloader type")
    host: str = Field(
        default="http://172.17.0.1:8080", alias="host", description="Downloader host"
    )
    username: str = Field(
        default="admin", alias="username", description="Downloader username"
    )
    password: str = Field(
        default="adminadmin", alias="password", description="Downloader password"
    )
    path: str = Field(default="/Downloads/Bangumi", description="Downloader path")
    ssl: bool = Field(default=False, description="Downloader ssl")

    @field_validator("host", mode="before")
    def validate_host(cls, value: str) -> str:
        # 如果输入值没有以 http:// 或 https:// 开头，自动加上 http://
        if not value.startswith(("http://", "https://")):
            value = f"http://{value}"
        return value


if __name__ == "__main__":
    host = "127.0.0.1:8999"
    print(Config(host=host, path="nnone"))
