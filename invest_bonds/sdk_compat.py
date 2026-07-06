from __future__ import annotations

import logging
import os

UNKNOWN_ENUM_MESSAGE = "Было получено неизвестное значение"
SDK_GRPC_HELPERS_LOGGER = "t_tech.invest._grpc_helpers"


class UnknownEnumWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return UNKNOWN_ENUM_MESSAGE not in record.getMessage()


def configure_t_invest_sdk() -> None:
    """Keep newer server enum values from polluting normal CLI output."""
    os.environ.setdefault("USE_DEFAULT_ENUM_IF_ERROR", "true")

    logger = logging.getLogger(SDK_GRPC_HELPERS_LOGGER)
    if not any(isinstance(item, UnknownEnumWarningFilter) for item in logger.filters):
        logger.addFilter(UnknownEnumWarningFilter())
