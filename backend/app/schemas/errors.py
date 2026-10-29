from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "code": "not_found",
                        "message": "Case not found",
                        "details": None,
                        "request_id": "3f2b9c1e5a7d4e68a1b2c3d4e5f60718",
                    }
                }
            ]
        }
    )

    error: ErrorBody