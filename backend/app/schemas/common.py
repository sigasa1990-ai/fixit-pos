from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class SuccessResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: dict | None = None
