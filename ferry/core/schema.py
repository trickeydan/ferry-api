from http import HTTPStatus
from typing import Any, Literal

from pydantic import BaseModel, model_validator


class ErrorDetail(BaseModel):
    status: Literal["error"] = "error"
    status_code: HTTPStatus
    status_name: str = ""
    detail: str | list[str] | list[dict[str, Any]]

    @model_validator(mode="before")
    @classmethod
    def populate_status_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            status_code = data.get("status_code")
            data["status_name"] = getattr(status_code, "name")
        return data
