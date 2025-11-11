"""Validation error handlers."""

from typing import Any

from fastapi.exceptions import RequestValidationError

from app.exceptions import HttpError


def loc_to_dot_sep(loc: tuple[str | int, ...]) -> str:
    path = ""
    new_loc = enumerate(loc[1:])  # Skip the first element (index 0)
    for i, x in new_loc:
        if isinstance(x, str):
            if i > 0:
                path += "."
            path += x
        elif isinstance(x, int):
            path += f"[{x}]"
        else:
            raise TypeError("Unexpected type")
    return path


def convert_errors(e: RequestValidationError) -> list[dict[str, Any]]:
    new_errors: list[dict[str, Any]] = e.errors()
    for error in new_errors:
        error["loc"] = loc_to_dot_sep(error["loc"])
    return new_errors


def generate_validation_error(exc: RequestValidationError) -> dict[str, Any]:
    field_errors = [
        {"field": err["loc"], "message": err["msg"]} for err in convert_errors(exc)
    ]
    error = {
        "code": "INVALID_INPUT",
        "message": "Validation Error",
        "errors": field_errors,
    }
    return error

__all__ = ["generate_validation_error"]
