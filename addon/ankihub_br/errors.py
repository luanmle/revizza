"""Sentry no add-on (T013). sentry-sdk é vendorizado no build do .ankiaddon;
se ausente (dev sem vendor) ou sem DSN no config, vira no-op silencioso."""


def init_error_reporting(sentry_dsn: str) -> None:
    if not sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        return
    sentry_sdk.init(dsn=sentry_dsn, default_integrations=False, send_default_pii=False)


def report_exception(exc: BaseException) -> None:
    try:
        import sentry_sdk
    except ImportError:
        return
    sentry_sdk.capture_exception(exc)
