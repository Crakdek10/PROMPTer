from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class AppError(Exception):
    message: str
    code: str = "APP_ERROR"
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)
    cause: Optional[Exception] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload

class ValidationAppError(AppError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=400, details=details or {})

class ConfigError(AppError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message=message, code="CONFIG_ERROR", status_code=400, details=details or {})

class ProviderError(AppError):
    def __init__(self, message: str, *, provider: str = "", details: Optional[dict[str, Any]] = None) -> None:
        d = details or {}
        if provider:
            d = {**d, "provider": provider}
        super().__init__(message=message, code="PROVIDER_ERROR", status_code=502, details=d)