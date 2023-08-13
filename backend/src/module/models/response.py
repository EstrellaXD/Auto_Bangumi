from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    status: bool = Field(..., example=True)
    status_code: int = Field(..., example=200)
    msg_en: str
    msg_zh: str


class APIResponse(BaseModel):
    msg_en: str = Field(..., example="Success")
    msg_zh: str = Field(..., example="成功")