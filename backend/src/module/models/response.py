from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    status: bool = Field(..., example=True)
    status_code: int = Field(..., example=200)
    msg_en: str
    msg_zh: str
    data: dict | None = None


class APIResponse(BaseModel):
    status: bool = Field(..., example=True)
    msg_en: str = Field(..., example="Success")
    msg_zh: str = Field(..., example="成功")