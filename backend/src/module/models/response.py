from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    status: bool = Field(..., json_schema_extra={"example": True})
    status_code: int = Field(..., json_schema_extra={"example": 200})
    msg_en: str
    msg_zh: str
    data: dict | None = None


class APIResponse(BaseModel):
    status: bool = Field(..., json_schema_extra={"example": True})
    msg_en: str = Field(..., json_schema_extra={"example": "Success"})
    msg_zh: str = Field(..., json_schema_extra={"example": "成功"})
