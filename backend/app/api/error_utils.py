"""Shared helpers for consistent API error handling."""

from __future__ import annotations

import logging

from flask import jsonify
from flask.typing import ResponseReturnValue

logger = logging.getLogger(__name__)

GENERIC_INTERNAL_ERROR_MESSAGE = "Internal server error"
GENERIC_BAD_REQUEST_MESSAGE = "Invalid request parameters"


def json_error(message: str, status_code: int) -> ResponseReturnValue:
    return jsonify({"error": message}), status_code


def handle_bad_request(
    log_message: str,
    exc: Exception,
    client_message: str = GENERIC_BAD_REQUEST_MESSAGE,
) -> ResponseReturnValue:
    logger.warning("%s: %s", log_message, exc)
    return json_error(client_message, 400)


def handle_internal_error(
    log_message: str,
    client_message: str = GENERIC_INTERNAL_ERROR_MESSAGE,
) -> ResponseReturnValue:
    logger.exception(log_message)
    return json_error(client_message, 500)
