"""Platform directories of the agent (``platformdirs``, app name ``TeTengoCaptura``)."""

from pathlib import Path

NOMBRE_APP = "TeTengoCaptura"


def datos() -> Path:
    """Outbox database and pending clips (e.g. ``%LOCALAPPDATA%\\TeTengoCaptura``)."""
    from platformdirs import user_data_path

    return user_data_path(NOMBRE_APP, appauthor=False)


def logs() -> Path:
    from platformdirs import user_log_path

    return user_log_path(NOMBRE_APP, appauthor=False)
