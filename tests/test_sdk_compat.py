import logging

from invest_bonds.sdk_compat import SDK_GRPC_HELPERS_LOGGER, configure_t_invest_sdk


def test_unknown_enum_warning_is_filtered(caplog) -> None:
    configure_t_invest_sdk()
    logger = logging.getLogger(SDK_GRPC_HELPERS_LOGGER)

    with caplog.at_level(logging.WARNING, logger=SDK_GRPC_HELPERS_LOGGER):
        logger.warning("Было получено неизвестное значение '7' для enum 'AccountType'")
        logger.warning("Different warning")

    assert "AccountType" not in caplog.text
    assert "Different warning" in caplog.text
